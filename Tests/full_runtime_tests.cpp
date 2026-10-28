#include "content/LearnSourceIndex.hpp"
#include "content/SourceLibraryCatalog.hpp"
#include "content/BookContextSourceCatalog.hpp"
#include "content/CurriculumShardCatalog.hpp"
#include "content/LessonCatalog.hpp"
#include "tasks/InstalledManualTaskRegistry.hpp"
#include <filesystem>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv){try{
    if(argc!=2)throw std::invalid_argument("exact runtime root required");
    const auto root=std::filesystem::canonical(argv[1]);
    const auto shards=fathom::curriculum::discoverShards(root/"curriculum-shards");
    if(shards.shardCount!=4||shards.sourceRecords!=432)throw std::runtime_error("Source-only shard discovery changed");
    const auto index=fathom::learn::SourceIndex::load(root/"learn-source-index");
    if(index->levels().size()!=105||index->exercises().empty())throw std::runtime_error("Full source index unavailable");
    const auto library=fathom::curriculum::SourceLibrary::load(root/"source-library");
    if(library.workbooks().size()!=105)throw std::runtime_error("Full source library unavailable");
    const auto contexts=fathom::curriculum::BookContextSourceCatalog::load(root/"book-context105",library);
    if(contexts.books().size()!=105)throw std::runtime_error("Full workbook contexts unavailable");
    std::vector<std::filesystem::path> extensions;
    for(const auto& name:fathom::lesson::Catalog::installedExtensionDirectoryNames())extensions.push_back(root/name);
    const auto catalog=fathom::lesson::Catalog::loadInstalled(root/"representative-controls",extensions);
    const auto admission=catalog->admit("fg:item:000002","fg:variant:000006");
    if(!admission||!admission->practiceAllowed()||!admission->model()
       ||admission->model()->source().syntheticFixture)throw std::runtime_error("Original reviewed Practice admission unavailable");
    const auto practice=admission->practiceConfiguration(44100,60);
    admission->validatePractice(practice);
    const std::size_t admitted=1;
    const auto manual=fathom::tasks::InstalledManualTaskRegistry::load(root/"typed-manual-tasks-v1");
    if(!manual.contains("level053/moduleb/p003-t1-r1-c2/cmajrp"))throw std::runtime_error("Original representative manual source unavailable");
    std::cout<<"PASS full runtime: 105 levels, 105 workbooks, 105 contexts, "<<admitted<<" bounded ordinary admissions; no audio/profile/native peer\n";
    return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
