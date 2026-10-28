#include "content/SourceLibraryCatalog.hpp"
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>
#include <cstdio>

namespace fathom::curriculum {
namespace {
using J=json::Value;
const J& at(const J& value,const std::string& key){return value.object().at(key);}
void require(bool condition,const std::string& message){if(!condition)throw std::runtime_error(message);}
std::size_t count(const J& value,std::size_t limit,const char* name){
    std::int64_t integer=0;require(value.integer(integer)&&integer>=0&&static_cast<std::uint64_t>(integer)<=limit,std::string{"Invalid "}+name);
    return static_cast<std::size_t>(integer);
}
std::filesystem::path safeFile(const std::filesystem::path& root,const std::string& name){
    require(!name.empty()&&name.find('\\')==std::string::npos&&name.find('\0')==std::string::npos,"Unsafe workbook asset path");
    const std::filesystem::path relative{name};
    require(!relative.is_absolute()&&!relative.has_root_name(),"Workbook asset path must be relative");
    auto current=root;
    for(const auto& part:relative){
        require(part!="."&&part!=".."&&part!="","Unsafe workbook asset component");
        current/=part;
        require(!std::filesystem::is_symlink(std::filesystem::symlink_status(current)),"Workbook asset symlink refused");
    }
    require(std::filesystem::is_regular_file(current),"Missing workbook asset: "+name);
    return current;
}
std::string exact(const std::filesystem::path& root,const std::string& name,std::size_t bytes,const std::string& hash,
    const content::CancellationCheck& canceled = {}){
    content::checkLoadCanceled(canceled);
    const auto file=safeFile(root,name);
    require(std::filesystem::file_size(file)==bytes,"Changed workbook asset size: "+name);
    const auto data=content::readBounded(file,bytes,canceled);
    require(data.size()==bytes&&content::sha256(data)==hash,"Changed workbook asset: "+name);
    content::checkLoadCanceled(canceled);
    return data;
}
void checkedRoot(const std::filesystem::path& root){
    require(root.is_absolute(),"Workbook library path must be absolute");
    auto current=std::filesystem::path{};
    for(const auto& part:root){current/=part;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(current)),"Workbook library root symlink refused");}
    require(std::filesystem::is_directory(root),"Workbook library missing");
}
std::set<std::string> actualFiles(const std::filesystem::path& root,const content::CancellationCheck& canceled){
    std::set<std::string> actual;
    for(const auto& entry:std::filesystem::recursive_directory_iterator(root)){
        content::checkLoadCanceled(canceled);
        require(!entry.is_symlink(),"Workbook library symlink refused");
        if(entry.is_regular_file())actual.insert(entry.path().lexically_relative(root).generic_string());
        else require(entry.is_directory(),"Unexpected workbook library entry");
    }
    return actual;
}
} // namespace

SourceLibrary SourceLibrary::load(const std::filesystem::path& installedResources,
    const content::CancellationCheck& canceled){
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    checkedRoot(installedResources);
    SourceLibrary library;
    library.root_=std::filesystem::canonical(installedResources);
    const auto handoffBytes=content::readBounded(safeFile(library.root_,"handoff.json"),1024*1024,canceled);
    require(content::sha256(handoffBytes)==FATHOM_SOURCE_LIBRARY_HANDOFF_SHA,"Unsupported or changed workbook library handoff");
    const auto handoff=json::parse(handoffBytes);
    checkpoint();
    require(at(handoff,"schema").string()=="fathom-source-library-handoff.1"&&at(handoff,"bundle_root").string()=="bundle","Unsupported workbook library handoff");
    const auto& indexRef=at(handoff,"index");
    require(at(indexRef,"path").string()=="index.json","Unexpected workbook library index path");
    const auto indexBytesCount=count(at(indexRef,"bytes"),1024*1024,"index byte count");
    const auto bundle=library.root_/"bundle";
    require(std::filesystem::is_directory(bundle)&&!std::filesystem::is_symlink(std::filesystem::symlink_status(bundle)),"Workbook library bundle missing or linked");
    const auto indexBytes=exact(bundle,"index.json",indexBytesCount,at(indexRef,"sha256").string(),canceled);
    require(content::sha256(indexBytes)==FATHOM_SOURCE_LIBRARY_INDEX_SHA,"Unsupported workbook library index");
    const auto index=json::parse(indexBytes);
    checkpoint();
    require(at(index,"schema").string()=="fathom-source-library.1"&&!at(index,"admitted").boolean()
        &&!at(index,"runtime_admission").boolean()&&!at(index,"whole_workbook_complete").boolean(),"Workbook library exceeds read-only scope");
    const auto& files=at(index,"files").object();
    const auto& entries=at(index,"entries").array();
    require(files.size()==210&&entries.size()==105,"Workbook library requires 105 original source pairs");
    std::set<std::string> declared{"handoff.json","bundle/index.json"};
    for(const auto& [name,descriptor]:files){
        checkpoint();
        require(name.rfind("assets/",0)==0,"Unexpected workbook library asset location");
        require(declared.insert("bundle/"+name).second,"Duplicate workbook library asset");
        exact(bundle,name,count(at(descriptor,"bytes"),1024*1024,"asset byte count"),at(descriptor,"sha256").string(),canceled);
    }
    require(actualFiles(library.root_,canceled)==declared,"Workbook library file set differs from sealed index");
    std::set<std::string> referenced;
    for(std::size_t position=0;position<entries.size();++position){
        checkpoint();
        const auto& entry=entries[position];
        const auto level=count(at(entry,"legacy_level"),105,"legacy level");
        require(level==position+1,"Workbook levels must be 1 through 105 in order");
        char id[32]{};std::snprintf(id,sizeof(id),"fg:workbook:%06zu",level);
        require(at(entry,"workbook_id").string()==id,"Workbook identity differs from level");
        SourceWorkbook workbook;
        workbook.id=id;workbook.level=static_cast<int>(level);workbook.label=at(entry,"label").string();
        require(!workbook.label.empty(),"Workbook title missing");
        const auto& txt=at(entry,"txt");const auto& pdf=at(entry,"pdf");
        for(const auto* ref:{&txt,&pdf}){
            const auto& name=at(*ref,"path").string();
            require(referenced.insert(name).second,"Workbook asset referenced twice");
            const auto found=files.find(name);require(found!=files.end(),"Workbook asset absent from index");
            require(at(found->second,"sha256").string()==at(*ref,"sha256").string()
                &&count(at(found->second,"bytes"),1024*1024,"asset size")==count(at(*ref,"bytes"),1024*1024,"asset size"),"Workbook entry and index disagree");
        }
        workbook.txt=safeFile(bundle,at(txt,"path").string());
        workbook.pdf=safeFile(bundle,at(pdf,"path").string());
        workbook.txtBytes=count(at(txt,"bytes"),1024*1024,"TXT byte count");
        workbook.pdfBytes=count(at(pdf,"bytes"),1024*1024,"PDF byte count");
        workbook.txtSha256=at(txt,"sha256").string();workbook.pdfSha256=at(pdf,"sha256").string();
        workbook.lines=count(at(txt,"line_count"),100000,"line count");
        workbook.pages=count(at(pdf,"page_count"),1000,"page count");
        require(workbook.lines>0&&workbook.pages>0,"Empty workbook source");
        library.workbooks_.push_back(std::move(workbook));
    }
    require(referenced.size()==files.size(),"Unreferenced workbook library assets");
    checkpoint();
    return library;
}

std::string SourceLibrary::instructions(const SourceWorkbook& workbook) const {
    require(workbook.level>=1&&workbook.level<=static_cast<int>(workbooks_.size())
        && &workbooks_[static_cast<std::size_t>(workbook.level-1)]==&workbook,"Workbook does not belong to this library");
    return exact(root_/"bundle",workbook.txt.lexically_relative(root_/"bundle").generic_string(),workbook.txtBytes,workbook.txtSha256);
}

std::filesystem::path SourceLibrary::originalPdf(const SourceWorkbook& workbook) const {
    require(workbook.level>=1&&workbook.level<=static_cast<int>(workbooks_.size())
        && &workbooks_[static_cast<std::size_t>(workbook.level-1)]==&workbook,"Workbook does not belong to this library");
    exact(root_/"bundle",workbook.pdf.lexically_relative(root_/"bundle").generic_string(),workbook.pdfBytes,workbook.pdfSha256);
    return workbook.pdf;
}
} // namespace fathom::curriculum
