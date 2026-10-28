#include "storage/ArchiveReader.hpp"
#include "content/Canonical.hpp"
#include <fstream>
#include <iostream>
#include <thread>
#include <sys/stat.h>
#include <unistd.h>

namespace {
using namespace fathom::storage;namespace fs=std::filesystem;using O=Value::Object;using A=Value::Array;
fs::path root,fixtures;A checks,cases;
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
std::string sha(const fs::path& p){return fathom::content::sha256(read(p));}
void writeNew(const fs::path& p,const std::string& bytes){if(fs::exists(p))throw std::runtime_error("Refuse overwrite");std::ofstream f(p,std::ios::binary);f<<bytes;f.close();if(!f)throw std::runtime_error("Evidence write failed");chmod(p.c_str(),0600);}
void check(const std::string& name,bool pass){checks.emplace_back(O{{"name",name},{"pass",pass}});std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';if(!pass)throw std::runtime_error(name);}
void directory(const fs::path& p){if(!fs::create_directory(p))throw std::runtime_error("Directory exists");chmod(p.c_str(),0700);}
void copyFixture(const fs::path& from,const fs::path& to){fs::copy_file(from,to);chmod(to.c_str(),0600);}
void verify(const std::string& name,const fs::path& input,const std::string& expected,
            const std::function<void(ArchiveReaderOptions&,A&)>& configure={}){
    auto initial=sha(input);A phases;ArchiveReaderOptions o;o.archive=input;o.candidateDirectory=root/(name+"-candidate");
    o.diagnosticHook=[&](const std::string& phase){phases.emplace_back(phase);};
    if(configure)configure(o,phases);
    Value receipt;std::string code="PASS",message;
    try{receipt=previewProfileArchive(o);}catch(const EnvelopeError& e){code=e.code;message=e.what();}
    cases.emplace_back(O{{"name",name},{"expected",expected},{"actual",code},{"message",message},{"phases",phases},{"receipt",receipt},{"input",input.string()},{"original_input_sha256",initial}});
    check(name+" exact disposition",code==expected);
    if(expected=="PASS"){
        check(name+" isolated stopped preview",at(receipt,"candidate_validated")==Value(true)&&at(receipt,"restore_performed")==Value(false)&&at(receipt,"archive_published")==Value(false)&&at(receipt,"required_resume_state")==Value("stopped"));
        check(name+" original archive bound",at(at(receipt,"archive"),"sha256")==Value(initial));
        check(name+" exact extracted profile",at(at(receipt,"profile_file"),"sha256")==Value(sha(o.candidateDirectory/"profile.sqlite"))&&at(at(receipt,"manifest"),"profile_sha256")==at(at(receipt,"profile_file"),"sha256"));
        check(name+" exact canonical manifest",canonical(at(receipt,"manifest"))==read(o.candidateDirectory/"manifest.json"));
        check(name+" standalone no sidecars",!fs::exists(o.candidateDirectory/"profile.sqlite-wal")&&!fs::exists(o.candidateDirectory/"profile.sqlite-shm")&&!fs::exists(o.candidateDirectory/"profile.sqlite-journal"));
        struct stat d{},p{},m{};check(name+" private stage",stat(o.candidateDirectory.c_str(),&d)==0&&(d.st_mode&0777)==0700&&stat((o.candidateDirectory/"profile.sqlite").c_str(),&p)==0&&(p.st_mode&0777)==0600&&stat((o.candidateDirectory/"manifest.json").c_str(),&m)==0&&(m.st_mode&0777)==0600);
    }else check(name+" no success receipt",receipt.null());
    check(name+" selected bytes retained",sha(input)==initial);
}
void generated(){
    auto list=parseCanonical(read(fixtures/"cases.json"));
    for(const auto& item:list.array()){
        const auto input=fixtures/at(item,"path").string();auto name=at(item,"name").string();
        check(name+" frozen fixture",sha(input)==at(item,"sha256").string());
        verify(name,input,at(item,"expected").string());
        if(auto phase=item.find("required_phase")){
            bool reached=false;for(const auto& observed:at(cases.back(),"phases").array())if(observed==*phase)reached=true;
            check(name+" required parser/extraction phase",reached);
        }
    }
}
void lifecycle(){
    const std::vector<std::pair<std::string,std::string>> specs{
        {"cancel-extract","ARCHIVE_CANCELLED"},{"cancel-sql","ARCHIVE_CANCELLED"},{"cancel-receipt","ARCHIVE_CANCELLED"},{"elapsed-deadline","ARCHIVE_DEADLINE"},
        {"source-replacement","ARCHIVE_CHANGED"},{"candidate-replacement","ARCHIVE_CHANGED"},{"manifest-replacement","ARCHIVE_CHANGED"},
        {"directory-replacement","ARCHIVE_CHANGED"},{"sidecar","ARCHIVE_DATABASE"},{"symlink-output","ARCHIVE_PATH"},
        {"existing-stage","ARCHIVE_DESTINATION_EXISTS"},{"invalid-timeout","ARCHIVE_OPTIONS"}};
    for(const auto& spec:specs){
        const auto& name=spec.first;auto input=root/(name+".zip");copyFixture(fixtures/"native-rich.zip",input);
        bool reached=false,cancel=false;const auto candidate=root/(name+"-candidate");
        verify(name,input,spec.second,[&](ArchiveReaderOptions& o,A& phases){
            if(name=="existing-stage"){directory(candidate);writeNew(candidate/"prior.txt","Retain prior candidate");reached=true;}
            if(name=="invalid-timeout"){o.timeout=std::chrono::milliseconds(0);reached=true;}
            if(name=="elapsed-deadline")o.timeout=std::chrono::milliseconds(5000);
            o.cancelled=[&]{return cancel;};
            o.diagnosticHook=[&](const std::string& phase){
                phases.emplace_back(phase);if(reached)return;
                bool trigger=(name=="cancel-extract"&&phase=="extract_chunk")||(name=="cancel-sql"&&phase=="sql_inspection")||(name=="cancel-receipt"&&phase=="before_receipt");
                if(trigger){reached=true;cancel=true;return;}
                if(name=="elapsed-deadline"&&phase=="sql_inspection"){
                    reached=true;std::this_thread::sleep_for(std::chrono::milliseconds(5100));return;
                }
                if(name=="source-replacement"&&phase=="before_sql"){
                    reached=true;fs::rename(input,root/(name+"-original.zip"));copyFixture(root/(name+"-original.zip"),input);
                }
                if((name=="candidate-replacement"&&phase=="extracted")||(name=="manifest-replacement"&&phase=="sql_verified")){
                    reached=true;auto file=candidate/(name=="candidate-replacement"?"profile.sqlite":"manifest.json");auto old=candidate/(file.filename().string()+".original");fs::rename(file,old);copyFixture(old,file);
                }
                if(name=="directory-replacement"&&phase=="before_receipt"){
                    reached=true;fs::rename(candidate,root/(name+"-original"));directory(candidate);
                }
                if(name=="sidecar"&&phase=="before_sql"){reached=true;writeNew(candidate/"profile.sqlite-wal","not a valid sidecar");}
                if(name=="symlink-output"&&phase=="extract_chunk"){
                    reached=true;writeNew(root/"victim.txt","Preserve selected target");fs::create_symlink(root/"victim.txt",candidate/"profile.sqlite");
                }
            };
        });
        check(name+" actual target phase reached",reached);
        if(name=="existing-stage")check(name+" prior bytes retained",read(candidate/"prior.txt")=="Retain prior candidate");
        if(name=="symlink-output")check(name+" target retained",read(root/"victim.txt")=="Preserve selected target");
    }
    auto link=root/"selected-symlink.zip";fs::create_symlink(fixtures/"native-rich.zip",link);verify("selected-symlink",link,"ARCHIVE_PATH");
}
}
int main(int argc,char** argv){
    if(argc!=2){std::cerr<<"Usage: archive_reader_tests /absolute/E\n";return 64;}
    bool owned=false,passed=false;
    try{
        auto e=fs::canonical(argv[1]);fixtures=e/"fixtures";root=e/"test-data"/"reader01";
        fs::create_directories(root.parent_path());chmod(root.parent_path().c_str(),0700);directory(root);owned=true;
        generated();lifecycle();passed=true;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(owned)writeNew(root/"failure.txt",e.what());}
    if(owned)writeNew(root/"checks.json",canonical(O{{"status",passed?"PASS":"FAIL"},{"synthetic",true},{"human_work",false},{"checks",checks},{"cases",cases}}));
    std::cout<<checks.size()<<" checks, "<<(passed?"PASS":"FAIL")<<'\n';return passed?0:1;
}
