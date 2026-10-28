#include "storage/HistoryCsv.hpp"
#include "content/Canonical.hpp"
#include <iostream>

int main(int argc,char** argv){using namespace fathom;using namespace fathom::storage;try{
    if((argc!=4&&argc!=5)||std::string(argv[1])!="--stopped-and-reconciled")throw std::runtime_error("Usage: fathom_history_csv --stopped-and-reconciled /absolute/profile/profile.sqlite /absolute/new-output.text-v2.csv [absolute-selection.json]; null/all or unique finalized UUID array. No defaults/overwrite.");
    Value selected;if(argc==5){std::filesystem::path p=argv[4];if(!p.is_absolute())throw std::runtime_error("Explicit absolute selection path required");selected=json::parse(content::readBounded(p,1024*1024));}
    StoreOptions options;options.path=argv[2];options.create=false;ProfileStore store(options);auto snapshot=store.snapshot("history-csv-export").get();
    if(!historyMaintenanceQuiescent(snapshot))throw std::runtime_error("Maintenance deferred: reconcile original pending/checkpoint/unfinalized outcomes before export. No output published.");
    auto view=historyCsv(snapshot,selected);auto receipt=publishHistoryCsv(argv[3],view);std::cout<<canonical(Value::Object{{"publication",receipt},{"report",view.report}})<<'\n';std::cout.flush();if(!std::cout)throw std::runtime_error("CSV was published but export report delivery failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
