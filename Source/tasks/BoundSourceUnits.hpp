#pragma once
#include "content/StrictJson.hpp"
#include <filesystem>
#include <string>
#include <vector>
namespace fathom::tasks::bound_source_units {
struct Row { const char* key; const char* value; const char* closure; const char* original; };
struct Context { const char* path; const char* value; };
void configureRoot(const std::filesystem::path&);
const std::vector<Row>& rows();
const std::vector<Context>& contexts();
bool exactKey(const std::string&);
bool allowedKind(const std::string&);
bool cagedKey(const std::string&);
bool triadControlsKey(const std::string&);
bool coordinateOverrideKey(const std::string&);
const json::Value& operativeImplementation(const std::string&);
bool atomReportGuard(const json::Value&,const json::Value&,const json::Value::Object&);
bool bodilyStopReported(const json::Value&);
std::size_t cachedFilesHashed();
} // namespace fathom::tasks::bound_source_units
