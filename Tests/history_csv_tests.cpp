#include "storage/HistoryCsv.hpp"
#include "content/Canonical.hpp"
#include <fstream>
#include <algorithm>
#include <iostream>
#include <sys/stat.h>
#include <unistd.h>

namespace {
using namespace fathom;using namespace fathom::storage;using V=Value;using A=V::Array;using O=V::Object;
const V& f(const V& v,const std::string& k){auto p=v.find(k);if(!p)throw std::runtime_error("Missing fixture "+k);return *p;}
V read(const std::filesystem::path& p){return json::parse(content::readBounded(p,32*1024*1024));}
void save(const std::filesystem::path& p,const V& v){std::ofstream out(p);out<<canonical(v)<<'\n';if(!out)throw std::runtime_error("Cannot save synthetic evidence");}
V projection(const V& cases){A results;for(auto& c:cases.array()){O row{{"id",f(c,"id")}};try{Reply s;s.status=Status::Confirmed;s.data=f(c,"snapshot");if(auto status=c.find("unconfirmed");status&&*status==V(true))s.status=Status::Unresolved;auto v=historyCsv(s,f(c,"selection"));row.emplace("rows",v.rows);row.emplace("report",v.report);row.emplace("csv",v.bytes);row.emplace("quiescent",historyMaintenanceQuiescent(s));}catch(const std::exception& e){row.emplace("error",e.what());}results.emplace_back(row);}return results;}
V checks(const std::filesystem::path& e){if(!e.is_absolute()||e.filename().string().find("-evidence")==std::string::npos)throw std::runtime_error("Explicit synthetic evidence root");auto d=e/"test-data/checks02";if(mkdir(d.c_str(),0700)!=0)throw std::runtime_error("Fresh checks directory required");A checks;
 auto check=[&](const std::string& name,auto fn,bool error=false){O x{{"name",name},{"expected_error",error}};try{bool observed=fn();x.emplace("passed",!error&&observed);}catch(const std::exception& ex){x.emplace("error",ex.what());x.emplace("passed",error);}checks.emplace_back(x);};
 auto rounding=read(e/"fixtures/rounding.json");for(auto& spec:rounding.array()){auto name=f(spec,"id").string();auto& pair=f(spec,"q").array();std::int64_t n,den;if(!pair[0].integer(n)||!pair[1].integer(den))throw std::runtime_error("Invalid roundingfixture");auto expected=f(spec,"expected").string();auto kind=f(spec,"kind").string();check(name,[=](){return (kind=="seconds"?historySeconds(Rational(n,den)):historyTempo(Rational(n,den)))==expected;});}
 check("negative-quantity-refused",[]{historySeconds(Rational(-1));return true;},true);
 check("zero-denominator-refused",[]{historyTempo(Rational(1,0));return true;},true);
 auto encoded=read(e/"fixtures/edge-rows.json");auto bytes=encodeHistoryRows(encoded);{std::ofstream output(d/"edge.text-v2.csv",std::ios::binary);output<<bytes;if(!output)throw std::runtime_error("Cannot retain native encoder CSV");}
 check("declared20columns",[]{return historyCsvColumns().array().size()==20;});
 check("text-v2-null-empty",[&]{return bytes.find("text:,")!=std::string::npos&&bytes.find("text:text:already")!=std::string::npos;});
 check("CR-LF-NUL-visible",[&]{return bytes.find("\\r\\ncombo")!=std::string::npos&&bytes.find("\\u0000=1+1")!=std::string::npos;});
 check("all-physical-lines-CRLF",[&]{for(std::size_t i=0;i<bytes.size();++i)if(bytes[i]=='\n'&&(i==0||bytes[i-1]!='\r'))return false;return true;});
 auto invalid=encoded;invalid.array()[0].array().pop_back();check("reject-row-width",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[9]="1";check("reject-text-in-numeric",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[11]=V::fromInteger(1);check("reject-number-in-text",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[13]=json::parse("0.333");check("reject-wrong-active-scale",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[16]=json::parse("1e3");check("reject-scientific-rendering",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[16]=json::parse("-1");check("reject-negative-number",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[16]=true;check("reject-bool-number",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[0]=nullptr;check("reject-required-null",[&]{encodeHistoryRows(invalid);return true;},true);
 invalid=encoded;invalid.array()[0].array()[11]=std::string(1,static_cast<char>(0xff));check("reject-invalid-UTF8",[&]{encodeHistoryRows(invalid);return true;},true);
 V tooMany=A(100001,A{});check("row-capacity-refuses",[&]{encodeHistoryRows(tooMany);return true;},true);
 V empty=A{};check("empty-selection-header-only",[&]{auto s=encodeHistoryRows(empty);return std::count(s.begin(),s.end(),'\n')==1;});
 HistoryCsv view;view.rows=encoded;view.bytes=bytes;view.report=O{{"csv_sha256",content::sha256(bytes)}};auto path=d/"published.text-v2.csv";
 check("exclusive-publication",[&]{auto receipt=publishHistoryCsv(path,view);struct stat st{};return f(receipt,"published")==V(true)&&content::readBounded(path,64*1024*1024)==bytes&&stat(path.c_str(),&st)==0&&(st.st_mode&077)==0;});
 check("existing-output-refused",[&]{publishHistoryCsv(path,view);return true;},true);check("existing-output-preserved",[&]{return content::readBounded(path,64*1024*1024)==bytes;});
 auto symlink=d/"link.text-v2.csv";std::filesystem::create_symlink(path.filename(),symlink);check("symlink-output-refused",[&]{publishHistoryCsv(symlink,view);return true;},true);check("symlink-target-preserved",[&]{return content::readBounded(path,64*1024*1024)==bytes;});
 check("wrong-format-filename",[&]{publishHistoryCsv(d/"history.csv",view);return true;},true);check("relative-output-refused",[&]{publishHistoryCsv("relative.text-v2.csv",view);return true;},true);
 auto parent=d/"actual-parent";mkdir(parent.c_str(),0700);auto alias=d/"parent-alias";std::filesystem::create_directory_symlink(parent,alias);check("symlink-parent-refused",[&]{publishHistoryCsv(alias/"new.text-v2.csv",view);return true;},true);
 auto shared=d/"shared";mkdir(shared.c_str(),0700);chmod(shared.c_str(),0777);check("shared-writable-parent-refused",[&]{publishHistoryCsv(shared/"new.text-v2.csv",view);return true;},true);chmod(shared.c_str(),0700);
 auto readonly=d/"readonly";mkdir(readonly.c_str(),0700);chmod(readonly.c_str(),0500);check("unwritable-parent-refused",[&]{publishHistoryCsv(readonly/"new.text-v2.csv",view);return true;},true);chmod(readonly.c_str(),0700);
 check("missing-parent-refused",[&]{publishHistoryCsv(d/"absent/new.text-v2.csv",view);return true;},true);auto changed=view;changed.bytes+='X';check("mismatched-csv-report-refused",[&]{publishHistoryCsv(d/"mismatch.text-v2.csv",changed);return true;},true);
 check("no-leaked-staging-files",[&]{for(auto& item:std::filesystem::directory_iterator(d))if(item.path().extension()==".partial")return false;return true;});
 int passed=0;for(auto& x:checks)if(f(x,"passed")==V(true))++passed;V result=O{{"checks",checks},{"passed",V::fromInteger(passed)},{"total",V::fromInteger(static_cast<std::int64_t>(checks.size()))},{"edge_csv_sha256",content::sha256(bytes)}};save(d/"results.json",result);return result;
}
V native(const std::filesystem::path& e){if(!e.is_absolute()||e.filename().string().find("-evidence")==std::string::npos)throw std::runtime_error("Explicit synthetic evidence root");auto d=e/"test-data/native01";if(mkdir(d.c_str(),0700)!=0)throw std::runtime_error("Fresh native evidence directory");StoreOptions o;o.path=e/"fixtures/native-profile/profile.sqlite";ProfileStore store(o);auto before=store.snapshot("csv-before").get();if(!historyMaintenanceQuiescent(before))throw std::runtime_error("Synthetic fixture not reconciled");auto all=historyCsv(before);auto receipt=publishHistoryCsv(d/"native.text-v2.csv",all);auto after=store.snapshot("csv-after").get();bool same=before.status==Status::Confirmed&&after.status==Status::Confirmed&&before.data==after.data;V result=O{{"before",before.data},{"after",after.data},{"rows",all.rows},{"report",all.report},{"receipt",receipt},{"passed",same},{"claim","actual native Store snapshot/export; existing raw SQLite layout may checkpoint but authoritative rows unchanged"}};save(d/"results.json",result);return result;}
}
int main(int argc,char** argv){try{if(argc!=3)throw std::runtime_error("Explicit --project cases.json, --checks evidence-root or --native evidence-root");V out;if(std::string(argv[1])=="--project")out=projection(read(argv[2]));else if(std::string(argv[1])=="--checks")out=checks(argv[2]);else if(std::string(argv[1])=="--native")out=native(argv[2]);else throw std::runtime_error("Unknown explicit test mode");std::cout<<canonical(out)<<'\n';if(auto total=out.find("total"))return *total==f(out,"passed")?0:1;if(auto pass=out.find("passed"))return *pass==V(true)?0:1;return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
