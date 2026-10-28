#include "storage/ProfileStore.hpp"
#include "storage/ProfileNaming.hpp"
#include "storage/ArchiveManifest.hpp"
#include "storage/SuiteReview.hpp"
#include "storage/StoredZip64.hpp"
#include "storage/ArchiveReader.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include "ProfileSchema.generated.hpp"
#include "sqlite3.h"
#include <algorithm>
#include <atomic>
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <charconv>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <fcntl.h>
#include <limits>
#include <mutex>
#include <regex>
#include <set>
#include <thread>
#include <cerrno>
#include <sys/stat.h>
#include <unistd.h>

namespace fathom::storage {
namespace {
using Object=Value::Object;
using Array=Value::Array;
Value num(std::int64_t n){return Value::fromInteger(n);}
struct Blob {std::string bytes;bool operator==(const Blob& x)const{return bytes==x.bytes;}};
using Cell=std::variant<std::nullptr_t,std::int64_t,std::string,Blob>;
using Row=std::vector<Cell>;using Rows=std::vector<Row>;
struct Failure:std::runtime_error {Status status;std::string code;Failure(Status s,std::string c,std::string m):std::runtime_error(std::move(m)),status(s),code(std::move(c)){};};
struct SqlFailure:std::runtime_error {int code;SqlFailure(int c,std::string s):std::runtime_error(std::move(s)),code(c){};};
void need(bool ok,const std::string& message,const std::string& code="INVALID_STORE"){if(!ok)throw Failure(Status::DefiniteFailure,code,message);}
void conflict(bool ok,const std::string& message){if(!ok)throw Failure(Status::Conflict,"CONFLICT",message);}
const Value& field(const Value& v,const std::string& key){auto p=v.find(key);need(p!=nullptr,"Missing field: "+key);return *p;}
std::string string(const Value& v){need(v.isString(),"Expected text");return v.string();}
std::string string(const Value& v,const std::string& key){return string(field(v,key));}
std::int64_t integer(const Value& v,std::int64_t min=0){std::int64_t n;need(v.integer(n)&&n>=min&&canonical(v)==std::to_string(n),"Expected canonical integer");return n;}
std::string txt(const Cell& c){need(std::holds_alternative<std::string>(c),"Unexpected SQL TEXT type");return std::get<std::string>(c);}
std::string blob(const Cell& c){need(std::holds_alternative<Blob>(c),"Unexpected SQL BLOB type");return std::get<Blob>(c).bytes;}
std::int64_t number(const Cell& c){need(std::holds_alternative<std::int64_t>(c),"Unexpected SQL INTEGER type");return std::get<std::int64_t>(c);}
bool null(const Cell& c){return std::holds_alternative<std::nullptr_t>(c);}
Value optionalText(const Cell& c){return null(c)?Value(nullptr):Value(txt(c));}
void nonempty(const std::string& s){need(!s.empty()&&s.find_first_not_of(" \r\n\t")!=std::string::npos,"Expected nonempty text");}
void digest(const std::string& s){need(std::regex_match(s,std::regex("[0-9a-f]{64}")),"Expected SHA256");}
void itemId(const std::string& s){need(std::regex_match(s,std::regex("fg:item:[0-9]{6}")),"Expected canonical item identity");}
std::string hex(const std::string& s){const char* digits="0123456789abcdef";std::string out;out.reserve(s.size()*2);for(unsigned char c:s){out+=digits[c>>4];out+=digits[c&15];}return out;}
Value cellValue(const Cell& c){if(null(c))return nullptr;if(std::holds_alternative<std::int64_t>(c))return num(number(c));if(std::holds_alternative<Blob>(c))return Object{{"blob_hex",hex(blob(c))}};return txt(c);}
Value rowValues(const Rows& rows){Array out;for(const auto& row:rows){Array values;for(const auto& c:row)values.push_back(cellValue(c));out.push_back(std::move(values));}return out;}
class Database {
public:
 sqlite3* handle=nullptr;
 std::function<void()> progress;
 std::exception_ptr progressError;
 void checkProgress(){if(progressError)std::rethrow_exception(progressError);if(progress)progress();}
 static int progressCallback(void* raw) noexcept {auto* self=static_cast<Database*>(raw);try{self->checkProgress();return 0;}catch(...){self->progressError=std::current_exception();return 1;}}
 void setProgress(std::function<void()> check){progress=std::move(check);progressError=nullptr;if(handle)sqlite3_progress_handler(handle,progress?1000:0,progress?&Database::progressCallback:nullptr,this);}
 Database()=default;~Database(){if(handle)sqlite3_close_v2(handle);}
 Database(const Database&)=delete;Database& operator=(const Database&)=delete;
 void open(const std::string& path,int flags){int rc=sqlite3_open_v2(path.c_str(),&handle,flags|SQLITE_OPEN_NOMUTEX,nullptr);if(rc!=SQLITE_OK)throw SqlFailure(rc,handle?sqlite3_errmsg(handle):"SQLite open failed");sqlite3_extended_result_codes(handle,1);sqlite3_busy_timeout(handle,250);}
 void close(){if(handle){int rc=sqlite3_close(handle);if(rc!=SQLITE_OK)throw SqlFailure(rc,sqlite3_errmsg(handle));handle=nullptr;}}
 void script(const std::string& sql){checkProgress();char* error=nullptr;int rc=sqlite3_exec(handle,sql.c_str(),nullptr,nullptr,&error);std::string message=error?error:"";sqlite3_free(error);checkProgress();if(rc!=SQLITE_OK)throw SqlFailure(rc,message);}
 void visit(const std::string& sql,const std::function<void(const Row&)>& each,const Row& params={}){
  checkProgress();
  sqlite3_stmt* raw=nullptr;int rc=sqlite3_prepare_v2(handle,sql.c_str(),-1,&raw,nullptr);if(rc!=SQLITE_OK)throw SqlFailure(rc,sqlite3_errmsg(handle));std::unique_ptr<sqlite3_stmt,decltype(&sqlite3_finalize)> stmt(raw,sqlite3_finalize);
  need(sqlite3_bind_parameter_count(raw)==static_cast<int>(params.size()),"SQL parameter count");
  for(std::size_t i=0;i<params.size();++i){const auto& c=params[i];int index=static_cast<int>(i)+1;if(null(c))rc=sqlite3_bind_null(raw,index);else if(std::holds_alternative<std::int64_t>(c))rc=sqlite3_bind_int64(raw,index,number(c));else if(std::holds_alternative<Blob>(c)){const auto& b=std::get<Blob>(c).bytes;rc=sqlite3_bind_blob64(raw,index,b.data(),b.size(),SQLITE_TRANSIENT);}else{const auto& s=std::get<std::string>(c);rc=sqlite3_bind_text64(raw,index,s.data(),s.size(),SQLITE_TRANSIENT,SQLITE_UTF8);}if(rc!=SQLITE_OK)throw SqlFailure(rc,sqlite3_errmsg(handle));}
  checkProgress();
  while((rc=sqlite3_step(raw))==SQLITE_ROW){Row row;for(int i=0;i<sqlite3_column_count(raw);++i){auto type=sqlite3_column_type(raw,i);if(type==SQLITE_NULL)row.emplace_back(nullptr);else if(type==SQLITE_INTEGER)row.emplace_back(static_cast<std::int64_t>(sqlite3_column_int64(raw,i)));else if(type==SQLITE_BLOB){auto p=static_cast<const char*>(sqlite3_column_blob(raw,i));int n=sqlite3_column_bytes(raw,i);need(n>=0,"Invalid stored BLOB length");row.emplace_back(Blob{n?std::string(p,static_cast<std::size_t>(n)):std::string{}});}else if(type==SQLITE_TEXT){auto p=reinterpret_cast<const char*>(sqlite3_column_text(raw,i));auto n=sqlite3_column_bytes(raw,i);need(n>=0,"Invalid stored TEXT length");row.emplace_back(std::string(p,static_cast<std::size_t>(n)));}else throw Failure(Status::DefiniteFailure,"SQL_TYPE","Unexpected REAL storage value");}checkProgress();each(row);checkProgress();}
  checkProgress();if(rc!=SQLITE_DONE)throw SqlFailure(rc,sqlite3_errmsg(handle));
 }
 Rows query(const std::string& sql,const Row& params={}){Rows rows;visit(sql,[&](const Row& row){rows.push_back(row);},params);return rows;}
};
std::int64_t scalar(Database& db,const std::string& sql){auto rows=db.query(sql);need(rows.size()==1&&rows[0].size()==1,"Expected scalar");return number(rows[0][0]);}
std::int64_t marker(Database& db){auto rows=db.query("SELECT value FROM metadata WHERE key='committed_seq'");need(rows.size()==1,"Missing receipt marker");auto s=txt(rows[0][0]);std::int64_t n=0;auto r=std::from_chars(s.data(),s.data()+s.size(),n);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size()&&n>=0&&std::to_string(n)==s,"Invalid receipt marker");return n;}
std::int64_t advance(Database& db){auto n=marker(db);need(n<std::numeric_limits<std::int64_t>::max(),"Receipt sequence exhausted");db.query("UPDATE metadata SET value=? WHERE key='committed_seq'",{std::to_string(n+1)});return n+1;}
std::string readonlyUri(const std::filesystem::path& path,bool immutable){
 const char* digits="0123456789ABCDEF";std::string uri="file:";for(unsigned char c:path.string()){if((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='/'||c=='-'||c=='_'||c=='.'||c=='~')uri+=static_cast<char>(c);else{uri+='%';uri+=digits[c>>4];uri+=digits[c&15];}}return uri+(immutable?"?immutable=1":"?readonly_shm=1");
}
Value fileIdentities(const std::filesystem::path& database){
 Object records;for(const auto& suffix:{"","-wal","-shm","-journal"}){
  struct stat st{};auto path=database.string()+suffix;
  if(lstat(path.c_str(),&st)!=0){need(errno==ENOENT,"Cannot inspect database sidecar identity");records[suffix]=nullptr;continue;}
  need(S_ISREG(st.st_mode),"Database/sidecar must remain regular");
  records[suffix]=Object{{"device",std::to_string(st.st_dev)},{"inode",std::to_string(st.st_ino)},{"bytes",std::to_string(st.st_size)},{"mtime_sec",std::to_string(st.st_mtimespec.tv_sec)},{"mtime_ns",std::to_string(st.st_mtimespec.tv_nsec)},{"ctime_sec",std::to_string(st.st_ctimespec.tv_sec)},{"ctime_ns",std::to_string(st.st_ctimespec.tv_nsec)}};
 }return records;
}
Rows schema(Database& db){return db.query("SELECT type,name,tbl_name,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name");}
const std::vector<std::string>& legacyAuthorities(){static const std::vector<std::string> names={"metadata","profile","session","session_close","identity","pending","finalized","checkpoint","late_evidence","acknowledgment","source_attestation","preferences","rule_observation"};return names;}
std::int64_t schemaVersion(Database& db){return scalar(db,"PRAGMA user_version");}
std::string schemaHash(Database& db){return content::sha256(schemaVersion(db)==1?profileSchemaV1Sql:profileSchemaSql);}
std::vector<std::string> authorities(Database& db){auto names=legacyAuthorities();if(schemaVersion(db)==2)names.push_back("suite_fact");return names;}
Value state(Database& db,bool observations){Object out;for(const auto& table:authorities(db))if(observations||table!="rule_observation")out.emplace(table,rowValues(db.query("SELECT * FROM "+table+" ORDER BY 1")));return out;}
std::string stateHash(Database& db,bool observations){return content::sha256(canonical(state(db,observations)));}
std::pair<std::string,Value> allocation(Database& db,const std::string& owner){auto rows=db.query("SELECT kind,context_bytes FROM identity WHERE owner=?",{owner});need(rows.size()==1,"Original activity identity is missing","MISSING_OWNER");return {txt(rows[0][0]),parseCanonical(blob(rows[0][1]))};}
void bind(Database& db,const Envelope& e){auto original=allocation(db,e.owner);need(original.first==e.kind&&canonical(original.second)==e.contextBytes,"Original allocated context mismatch");}
std::optional<Value> linkedContext(Database& db,const Value& v){if(field(v,"owner").null())return {};auto owner=string(v,"owner");auto original=allocation(db,owner);need(original.first=="Attempt","Freeplay cannot own a source attestation");return original.second;}
void uniqueAvailable(Database& db,const std::string& id){validateUuid(id);auto rows=db.query("SELECT profile_id FROM profile WHERE profile_id=? UNION ALL SELECT session_id FROM session WHERE session_id=? UNION ALL SELECT owner FROM identity WHERE owner=? UNION ALL SELECT event_key FROM late_evidence WHERE event_key=? UNION ALL SELECT fact_id FROM acknowledgment WHERE fact_id=? UNION ALL SELECT fact_id FROM source_attestation WHERE fact_id=? UNION ALL SELECT fact_id FROM rule_observation WHERE fact_id=?",{id,id,id,id,id,id,id});if(schemaVersion(db)==2){auto suiteRows=db.query("SELECT fact_id FROM suite_fact WHERE fact_id=?",{id});rows.insert(rows.end(),suiteRows.begin(),suiteRows.end());}conflict(rows.empty(),"UUID already belongs to another authoritative fact");}
std::string fresh(Database& db){for(int i=0;i<16;++i){auto id=newUuid();try{uniqueAvailable(db,id);return id;}catch(const Failure& f){if(f.status!=Status::Conflict)throw;}}throw Failure(Status::DefiniteFailure,"UUID_EXHAUSTED","Sixteen identity collision proposals exhausted");}
void inspect(Database& db){
 Database expected;expected.open(":memory:",SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE);auto version=schemaVersion(db);need(version==1||version==2,"Unsupported profile version","UNSUPPORTED_SCHEMA");expected.script(version==1?profileSchemaV1Sql:profileSchemaSql);
 need(schema(db)==schema(expected),"Unsupported or changed schema/trigger definitions","UNSUPPORTED_SCHEMA");need(scalar(db,"PRAGMA application_id")==1178686536&&(schemaVersion(db)==1||schemaVersion(db)==2),"Unsupported profile format","UNSUPPORTED_SCHEMA");std::int64_t integrityRows=0;db.visit("PRAGMA integrity_check",[&](const Row& r){need(r==Row{std::string("ok")}&&++integrityRows==1,"Corrupt authoritative database");});need(integrityRows==1,"Missing integrity result");db.visit("PRAGMA foreign_key_check",[](const Row&){need(false,"Corrupt authoritative relationships");});
 auto meta=db.query("SELECT key,value FROM metadata ORDER BY key LIMIT 3");need(meta.size()==2&&txt(meta[0][0])=="committed_seq"&&txt(meta[1][0])=="data_schema_version"&&txt(meta[1][1])==std::to_string(version),"Metadata identity mismatch");auto end=marker(db);
 auto profiles=db.query("SELECT * FROM profile LIMIT 2");need(profiles.size()==1&&number(profiles[0][0])==1&&txt(profiles[0][2])=="Fathom.LocalProfile","Profile identity mismatch");auto profile=txt(profiles[0][1]);validateUuid(profile);validateUtc(txt(profiles[0][3]));
 std::string previousId;db.visit(std::string("SELECT profile_id AS id FROM profile UNION ALL SELECT session_id FROM session UNION ALL SELECT owner FROM identity UNION ALL SELECT event_key FROM late_evidence UNION ALL SELECT fact_id FROM acknowledgment UNION ALL SELECT fact_id FROM source_attestation UNION ALL SELECT fact_id FROM rule_observation")+(version==2?" UNION ALL SELECT fact_id FROM suite_fact":"")+" ORDER BY id",[&](const Row& r){auto id=txt(r[0]);validateUuid(id);need(id!=previousId,"Cross-table UUID collision");previousId=id;});auto addId=[](const Cell& c){validateUuid(txt(c));};
 db.visit("SELECT * FROM session",[&](const Row& r){addId(r[0]);validateUtc(txt(r[1]));localDay(txt(r[1]),txt(r[2]));if(!null(r[3]))need(number(r[3])>0&&number(r[3])<=14400,"Session budget");if(!null(r[4]))need(parseCanonical(blob(r[4])).isObject(),"Session plan object");});
 db.visit("SELECT * FROM identity",[&](const Row& r){addId(r[0]);validateUtc(txt(r[3]));auto c=parseCanonical(blob(r[4]));validateContext(c,txt(r[1]));need((txt(r[1])=="Attempt"&&!null(r[2])&&txt(r[2])==string(c,"session_id"))||(txt(r[1])=="FreeplayActivity"&&null(r[2])),"Allocation session mismatch");});
 auto receipt=[](const Cell& c){need(number(c)>0,"Global receipt must be positive");};
 db.visit("SELECT * FROM finalized",[&](const Row& r){auto e=validateEnvelope(blob(r[1]));bind(db,e);need(txt(r[0])==e.owner&&txt(r[2])==e.digest,"Corrupt finalized payload identity");receipt(r[3]);need(txt(r[4])==e.practiceUtc&&txt(r[5])==e.timezone&&txt(r[6])==e.day&&txt(r[7])==std::to_string(e.active.numerator())&&txt(r[8])==std::to_string(e.active.denominator())&&txt(r[9])==e.outcome&&optionalText(r[10])==(e.assessment?Value(*e.assessment):Value(nullptr)),"Corrupt finalized typed summary");});
 db.visit("SELECT * FROM pending",[&](const Row& r){need(number(r[1])==1,"Pending version");auto e=validateEnvelope(blob(r[2]));bind(db,e);need(txt(r[0])==e.owner&&txt(r[3])==e.digest,"Corrupt pending identity");need(db.query("SELECT owner FROM finalized WHERE owner=?",{e.owner}).empty(),"Pending remains after final receipt");});
 db.visit("SELECT * FROM checkpoint",[&](const Row& r){auto owner=txt(r[0]);auto a=allocation(db,owner);validateCheckpoint(owner,number(r[1]),number(r[2]),blob(r[3]),a.first,a.second);need(db.query("SELECT owner FROM finalized WHERE owner=?",{owner}).empty(),"Checkpoint remains after final receipt");});
 db.visit("SELECT * FROM session_close",[&](const Row& r){auto key=txt(r[0]),at=txt(r[1]);validateUtc(at);auto session=db.query("SELECT started_utc FROM session WHERE session_id=?",{key});need(session.size()==1&&!utcBefore(at,txt(session[0][0])),"Session close precedes start");need(db.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE i.session_id=? AND f.owner IS NULL",{key}).empty(),"Closed unresolved Session");});
 db.visit("SELECT * FROM late_evidence",[&](const Row& r){addId(r[0]);validateUtc(txt(r[2]));auto b=blob(r[3]);auto v=parseCanonical(b);need(content::sha256(b)==txt(r[4])&&string(v,"original_owner")==txt(r[1]),"Corrupt late evidence");integer(field(v,"generation"));});
 db.visit("SELECT * FROM acknowledgment",[&](const Row& r){addId(r[0]);itemId(txt(r[1]));need(number(r[2])>0,"Acknowledgment revision");validateUtc(txt(r[3]));receipt(r[4]);});
 db.visit("SELECT * FROM source_attestation",[&](const Row& r){addId(r[0]);auto b=blob(r[12]);auto v=parseCanonical(b);validateAttestation(v,profile,linkedContext(db,v));need(content::sha256(b)==txt(r[13]),"Source fact digest mismatch");need(txt(r[0])==string(v,"fact_id")&&optionalText(r[1])==field(v,"owner")&&txt(r[2])==string(v,"item_id")&&number(r[3])==integer(field(v,"content_revision"),1)&&blob(r[4])==canonical(field(v,"rubric_ref"))&&blob(r[5])==canonical(field(v,"context"))&&txt(r[6])==string(v,"take_id")&&txt(r[7])==string(v,"work_id")&&txt(r[8])==profile&&txt(r[9])==string(v,"practice_utc")&&txt(r[10])==string(v,"timezone")&&txt(r[11])==string(v,"local_day"),"Source fact typed summary mismatch");receipt(r[14]);});
 db.visit("SELECT * FROM preferences",[&](const Row& r){nonempty(txt(r[0]));need(number(r[1])>0&&number(r[2])>0&&parseCanonical(blob(r[3])).isObject(),"Invalid preferences envelope");});
 db.visit("SELECT * FROM rule_observation",[&](const Row& r){addId(r[0]);Value v=Object{{"fact_id",txt(r[0])},{"rule_version",txt(r[1])},{"rule_config",blob(r[2])},{"rule_config_sha256",txt(r[3])},{"evidence_marker",num(number(r[4]))},{"evidence_sha256",txt(r[5])},{"content_selection",blob(r[6])},{"content_selection_sha256",txt(r[7])},{"as_of_utc",txt(r[8])},{"displayed_state",blob(r[9])},{"displayed_state_sha256",txt(r[10])}};validateRuleObservation(v);need(number(r[4])<=end,"Rule observation cites future receipt");});
 // Iterate actual rows, never an allocation or loop bounded by corrupt marker.
 if(version==2)(void)suite::projection(state(db,true));
 std::int64_t expectedSeq=0;db.visit(std::string("SELECT committed_seq AS seq FROM finalized UNION ALL SELECT committed_seq FROM acknowledgment UNION ALL SELECT committed_seq FROM source_attestation")+(version==2?" UNION ALL SELECT committed_seq FROM suite_fact":"")+" ORDER BY seq",[&](const Row& r){auto seq=number(r[0]);need(expectedSeq<std::numeric_limits<std::int64_t>::max()&&seq==expectedSeq+1,"Global receipt collision or gap");expectedSeq=seq;});need(expectedSeq==end,"Global receipt marker mismatch");
}
}
const char* statusName(Status s) noexcept{switch(s){case Status::Confirmed:return "Confirmed";case Status::DefinitelyAbsent:return "DefinitelyAbsent";case Status::Unresolved:return "Unresolved";case Status::Conflict:return "Conflict";case Status::DefiniteFailure:return "DefiniteFailure";case Status::Unsupported:return "Unsupported";case Status::Busy:return "Busy";}return "DefiniteFailure";}
namespace {
class SnapshotHash {
    CC_SHA256_CTX context{};
public:
    SnapshotHash(){need(CC_SHA256_Init(&context)==1,"Cannot initialize snapshot digest");}
    void add(const std::string& bytes,const std::function<void()>& check){
        for(std::size_t at=0;at<bytes.size();){
            check();
            auto count=std::min<std::size_t>(1048576,bytes.size()-at);
            need(CC_SHA256_Update(&context,bytes.data()+at,static_cast<CC_LONG>(count))==1,"Cannot update snapshot digest");
            at+=count;
        }
    }
    std::string finish(){
        std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> bytes{};
        need(CC_SHA256_Final(bytes.data(),&context)==1,"Cannot finish snapshot digest");
        return hex(std::string(reinterpret_cast<const char*>(bytes.data()),bytes.size()));
    }
};
Value streamedAuthority(Database& database,const std::function<void()>& check){
    SnapshotHash hash;
    auto tables=authorities(database);
    std::sort(tables.begin(),tables.end());
    Object counts;
    hash.add("{",check);
    bool firstTable=true;
    for(const auto& table:tables){
        check();
        hash.add((firstTable?"":",")+canonical(Value(table))+ ":[",check);
        firstTable=false;
        std::int64_t count=0;
        database.visit("SELECT * FROM "+table+" ORDER BY 1",[&](const Row& row){
            Array values;
            for(const auto& cell:row){check();values.push_back(cellValue(cell));}
            hash.add((count?",":"")+canonical(Value(std::move(values))),check);
            need(count<INT64_MAX,"Snapshot row count overflow");
            ++count;
        });
        hash.add("]",check);
        counts.emplace(table,num(count));
    }
    hash.add("}",check);
    return Object{{"sha256",hash.finish()},{"row_counts",counts},
                  {"encoding","storage-json.1 authoritative object; keys and SQL primary keys ordered"}};
}
ArchiveManifestBuilder makeArchiveProjection(Database& candidate,const std::string& profile,
        std::int64_t committed,const Value& authority){
    ArchiveManifestBuilder projection(profile,committed,schemaHash(candidate),
                                      string(authority,"sha256"),field(authority,"row_counts"),schemaVersion(candidate));
    const auto named=candidate.query("SELECT namespace_version,value_bytes FROM preferences WHERE key=?",{std::string(profile_names::key)});
    if(!named.empty()){const auto identity=parseCanonical(blob(named[0][1]));need(number(named[0][0])==1&&profile_names::valid(identity)&&identity.object().at("profile_id")==Value(profile),"Profile name metadata does not match its original UUID");projection.setProfileName(identity.object().at("display_name").string());}
    candidate.visit("SELECT context_bytes FROM identity WHERE kind='Attempt' UNION ALL SELECT context_bytes FROM source_attestation",
        [&](const Row& row){projection.addContext(parseCanonical(blob(row[0])));});
    candidate.visit("SELECT item_id,content_revision FROM acknowledgment",
        [&](const Row& row){projection.addAcknowledgment(txt(row[0]),number(row[1]));});
    candidate.visit("SELECT practice_utc FROM finalized UNION ALL SELECT practice_utc FROM source_attestation",
        [&](const Row& row){projection.addRecordedTime(txt(row[0]));});
    return projection;
}
Value restoreBoundary(Database& database,const std::function<void()>& check){
    database.setProgress(check);
    try{
        inspect(database);
        need(database.query("SELECT owner FROM pending LIMIT 1").empty()&&database.query("SELECT owner FROM checkpoint LIMIT 1").empty()&&
             database.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE f.owner IS NULL LIMIT 1").empty(),
             "Resolve original unfinished outcomes before restore","RESTORE_RECOVERY_REQUIRED");
        auto authority=streamedAuthority(database,check);
        Value out=Object{{"profile_id",txt(database.query("SELECT profile_id FROM profile")[0][0])},{"marker",num(marker(database))},
            {"schema_sha256",schemaHash(database)},{"authority_sha256",field(authority,"sha256")},{"authoritative_row_counts",field(authority,"row_counts")}};
        database.setProgress({});return out;
    }catch(...){database.setProgress({});throw;}
}
struct SnapshotFD {
    int value=-1;
    explicit SnapshotFD(int fd):value(fd){}
    ~SnapshotFD(){if(value>=0)::close(value);}
    SnapshotFD(const SnapshotFD&)=delete;
    SnapshotFD& operator=(const SnapshotFD&)=delete;
};
void publicationOutsideProfile(const std::filesystem::path& target,const std::filesystem::path& profile,
                               const std::filesystem::path& stage,bool reserveControlNames=true){
    need(target.is_absolute()&&target.lexically_normal()==target,"Explicit normalized backup target required","PUBLICATION_PATH");
    if(reserveControlNames){auto folded=target.filename().string();for(char& c:folded)if(c>='A'&&c<='Z')c=static_cast<char>(c-'A'+'a');
        need(folded.rfind(".fathom-backup-",0)!=0,"Reserved publication namespace","PUBLICATION_PATH");}
    std::vector<struct stat> protectedDirectories,protectedFiles;
    for(const auto& path:{profile.parent_path(),stage}){
        struct stat s{};
        if(lstat(path.c_str(),&s)==0){need(S_ISDIR(s.st_mode),"Protected backup directory changed","PUBLICATION_PATH");protectedDirectories.push_back(s);}
        else need(errno==ENOENT,"Cannot inspect protected directory","PUBLICATION_PATH");
    }
    for(const auto& path:{profile,stage/"profile.sqlite",stage/"manifest.json",stage/"candidate.zip"}){
        struct stat s{};
        if(lstat(path.c_str(),&s)==0)protectedFiles.push_back(s);
        else need(errno==ENOENT,"Cannot inspect protected file","PUBLICATION_PATH");
    }
    auto directory=target.parent_path();
    for(;;){
        struct stat s{};need(lstat(directory.c_str(),&s)==0&&S_ISDIR(s.st_mode),"Backup ancestors must exist without symlinks","PUBLICATION_PATH");
        for(const auto& protectedStat:protectedDirectories)
            need(s.st_dev!=protectedStat.st_dev||s.st_ino!=protectedStat.st_ino,"Backup target aliases protected directory ancestry","PUBLICATION_PATH");
        auto parent=directory.parent_path();if(parent==directory)break;directory=parent;
    }
    struct stat selected{};
    if(lstat(target.c_str(),&selected)==0){
        for(const auto& protectedStat:protectedFiles)
            need(selected.st_dev!=protectedStat.st_dev||selected.st_ino!=protectedStat.st_ino,"Backup target aliases a protected file","PUBLICATION_PATH");
    }else need(errno==ENOENT,"Cannot inspect selected backup target","PUBLICATION_PATH");
}
bool sameSnapshotStat(const struct stat& a,const struct stat& b){
    return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_size==b.st_size&&
           a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&
           a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;
}
struct stat pinnedSnapshotStat(int reserved,const std::filesystem::path& path){
    struct stat pinned{},named{};
    need(fstat(reserved,&pinned)==0&&lstat(path.c_str(),&named)==0&&S_ISREG(pinned.st_mode)&&
         S_ISREG(named.st_mode)&&pinned.st_uid==getuid()&&pinned.st_nlink==1&&
         (pinned.st_mode&077)==0&&pinned.st_size>=0&&sameSnapshotStat(pinned,named),
         "Snapshot no longer matches its exclusively created file","SNAPSHOT_CHANGED");
    return pinned;
}
Value closedSnapshotIdentity(int reserved,const std::filesystem::path& path,const struct stat& validated,
                             const std::function<void()>& check){
    need(sameSnapshotStat(validated,pinnedSnapshotStat(reserved,path)),
         "Snapshot changed after validation","SNAPSHOT_CHANGED");
    need(lseek(reserved,0,SEEK_SET)==0,"Cannot seek closed snapshot","SNAPSHOT_READ_FAILED");
    constexpr std::uint64_t limit=16ULL*1024*1024*1024;
    need(static_cast<std::uint64_t>(validated.st_size)<=limit,"Snapshot exceeds accepted capacity","SNAPSHOT_CAPACITY");
    SnapshotHash hash;
    std::vector<char> buffer(1048576);
    std::uint64_t total=0;
    for(;;){
        check();
        auto count=::read(reserved,buffer.data(),buffer.size());
        if(count<0&&errno==EINTR)continue;
        need(count>=0,"Cannot read snapshot chunk","SNAPSHOT_READ_FAILED");
        if(count==0)break;
        need(static_cast<std::uint64_t>(count)<=limit-total,"Snapshot grew beyond capacity","SNAPSHOT_CAPACITY");
        total+=static_cast<std::uint64_t>(count);
        hash.add(std::string(buffer.data(),static_cast<std::size_t>(count)),check);
    }
    need(sameSnapshotStat(validated,pinnedSnapshotStat(reserved,path))&&
         total==static_cast<std::uint64_t>(validated.st_size),
         "Snapshot changed while hashing","SNAPSHOT_CHANGED");
    return Object{{"bytes",num(static_cast<std::int64_t>(total))},{"sha256",hash.finish()}};
}
void snapshotParent(const std::filesystem::path& directory){
    need(directory.is_absolute()&&!directory.filename().empty(),"Explicit new absolute snapshot directory required");
    std::filesystem::path path;
    for(const auto& component:directory.parent_path()){
        need(component!="."&&component!="..","Snapshot traversal refused");
        path/=component;
        struct stat st{};
        need(lstat(path.c_str(),&st)==0&&S_ISDIR(st.st_mode),"Snapshot parent must exist without symlinks");
        if(path==directory.parent_path())need(st.st_uid==getuid()&&(st.st_mode&077)==0,"Snapshot parent must be private and user-owned");
    }
    need(directory.filename()!="."&&directory.filename()!="..","Snapshot directory traversal refused");
    struct stat st{};
    need(lstat(directory.c_str(),&st)!=0&&errno==ENOENT,"Snapshot destination already exists","SNAPSHOT_DESTINATION_EXISTS");
}
struct SnapshotProgress {
    Database& db;
    SnapshotProgress(Database& d,const std::function<void()>& check):db(d){db.setProgress(check);}
    ~SnapshotProgress(){db.setProgress({});}
};
struct SnapshotCopy {
    sqlite3_backup* handle=nullptr;
    ~SnapshotCopy(){if(handle)sqlite3_backup_finish(handle);}
};
} // namespace
namespace detail {
Value inspectArchiveCandidate(int descriptor,const std::filesystem::path& path,
        const std::function<void()>& check,const std::function<void(const std::string&)>& hook){
    try{
        check();const auto original=pinnedSnapshotStat(descriptor,path);
        auto stable=[&]{check();need(sameSnapshotStat(original,pinnedSnapshotStat(descriptor,path)),
                                   "Archive database changed during inspection","ARCHIVE_CHANGED");};
        for(const char* suffix:{"-wal","-shm","-journal"}){
            struct stat s{};need(lstat((path.string()+suffix).c_str(),&s)!=0&&errno==ENOENT,
                "Archive database must be standalone without sidecars","ARCHIVE_DATABASE");
        }
        std::array<unsigned char,100> header{};
        need(pread(descriptor,header.data(),header.size(),0)==static_cast<ssize_t>(header.size())&&
             header[18]==1&&header[19]==1,"Archive database must use standalone rollback format","ARCHIVE_DATABASE");
        Database db;db.open(readonlyUri(path,true),SQLITE_OPEN_READONLY|SQLITE_OPEN_URI);
        int previous=0;
        need(sqlite3_db_config(db.handle,SQLITE_DBCONFIG_DEFENSIVE,1,&previous)==SQLITE_OK&&
             sqlite3_db_config(db.handle,SQLITE_DBCONFIG_TRUSTED_SCHEMA,0,&previous)==SQLITE_OK&&
             sqlite3_db_config(db.handle,SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION,0,&previous)==SQLITE_OK,
             "Cannot configure readonly archive inspection","ARCHIVE_DATABASE");
        db.setProgress(stable);db.script("PRAGMA query_only=ON;PRAGMA cache_size=-8192;");
        if(hook)hook("sql_inspection");
        stable();inspect(db);
        need(txt(db.query("PRAGMA journal_mode")[0][0])=="delete","Archive database journal dependency refused","ARCHIVE_DATABASE");
        const auto pages=scalar(db,"PRAGMA page_count"),pageSize=scalar(db,"PRAGMA page_size");
        need(pages>0&&pageSize>0&&pages<=INT64_MAX/pageSize&&pages*pageSize==original.st_size,
             "Archive database byte extent differs from logical pages","ARCHIVE_DATABASE");
        need(db.query("SELECT owner FROM pending LIMIT 1").empty()&&db.query("SELECT owner FROM checkpoint LIMIT 1").empty()&&
             db.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE f.owner IS NULL LIMIT 1").empty(),
             "Archive contains unresolved original outcomes; reconcile them before backup","ARCHIVE_RECOVERY_REQUIRED");
        // External SQLite TEXT must be valid UTF-8 before canonical authority hashing.
        // BLOBs remain original bytes; their existing semantic validators govern them.
        for(const auto& table:authorities(db))db.visit("SELECT * FROM "+table,[&](const Row& row){
            for(const auto& c:row)if(std::holds_alternative<std::string>(c)){
                const auto& text=txt(c);auto encoded=canonical(Value(text));json::Limits limits;
                limits.bytes=encoded.size();limits.stringBytes=text.size();limits.values=1;
                need(json::parse(encoded,limits)==Value(text),"Archive TEXT must be valid UTF-8","ARCHIVE_DATABASE");
            }
        });
        const auto authority=streamedAuthority(db,stable);
        const auto profile=txt(db.query("SELECT profile_id FROM profile")[0][0]);
        auto projection=makeArchiveProjection(db,profile,marker(db),authority);
        db.setProgress({});db.close();stable();
        auto file=closedSnapshotIdentity(descriptor,path,original,stable);
        auto manifest=projection.manifest(integer(field(file,"bytes")),string(file,"sha256"));
        if(hook)hook("sql_verified");
        stable();
        for(const char* suffix:{"-wal","-shm","-journal"}){
            struct stat s{};need(lstat((path.string()+suffix).c_str(),&s)!=0&&errno==ENOENT,
                "Archive database acquired sidecars","ARCHIVE_DATABASE");
        }
        return manifest;
    }catch(const EnvelopeError& e){
        if(e.code=="ARCHIVE_CHANGED"||e.code=="ARCHIVE_CANCELLED"||e.code=="ARCHIVE_DEADLINE")throw;
        throw EnvelopeError("ARCHIVE_DATABASE",e.what());
    }
    catch(const Failure& e){throw EnvelopeError(e.code=="ARCHIVE_RECOVERY_REQUIRED"?e.code:
        (e.code=="ARCHIVE_CHANGED"||e.code=="SNAPSHOT_CHANGED")?"ARCHIVE_CHANGED":"ARCHIVE_DATABASE",e.what());}
    catch(const SqlFailure& e){throw EnvelopeError("ARCHIVE_DATABASE",e.what());}
    catch(const json::Error& e){throw EnvelopeError("ARCHIVE_DATABASE",e.what());}
}
} // namespace detail
struct ProfileStore::Impl {
 StoreOptions options;ProfileLease lease;Database db;std::string pendingRestoreOperation;struct stat openedDatabase{};std::thread worker;std::mutex mutex;std::condition_variable cv;bool closing=false,quarantined=false,inFlight=false,maintenance=false;std::set<std::string> queuedCheckpoints;
 std::atomic<bool> shutdownFinished{false};std::string shutdownFailure;
 struct Job{std::string operation,owner,checkpointOwner;bool maintenance=false,restoreReconcile=false,newAllocation=false;std::function<Reply()> run;std::promise<Reply> promise;};std::deque<Job> queue;
 explicit Impl(StoreOptions o):options(std::move(o)),lease(options.path,options.create){
  std::promise<void> ready;auto future=ready.get_future();worker=std::thread([this,p=std::move(ready)]()mutable{try{open();p.set_value();}catch(...){auto error=std::current_exception();try{db.close();}catch(...){}p.set_exception(error);return;}
   for(;;){Job job;{std::unique_lock<std::mutex> lock(mutex);cv.wait(lock,[this]{return closing||!queue.empty();});if(queue.empty()&&closing)break;job=std::move(queue.front());queue.pop_front();inFlight=true;if(!job.checkpointOwner.empty())queuedCheckpoints.erase(job.checkpointOwner);}
    Reply reply;try{if(quarantined&&!job.restoreReconcile){
     if(job.newAllocation)reply={Status::DefiniteFailure,job.operation,"","ALLOCATION_REFUSED_STORE_UNCERTAIN","No new activity was allocated. This profile still needs original-operation recovery; saved history and recovery records stay.",Object{{"version","allocation-refusal.1"},{"new_allocation","not_admitted"},{"job_executed",false},{"store_quarantined",true}}};
     else throw Failure(Status::Unresolved,"STORE_UNCERTAIN","Resolve the original uncertain operation before further work; retain original key and bytes");
    }else{hook("before_operation",job.operation);reply=job.run();}}catch(const Failure& f){reply={f.status,job.operation,job.owner,f.code,f.what(),nullptr};}catch(const EnvelopeError& f){reply={Status::DefiniteFailure,job.operation,job.owner,f.code,f.what(),nullptr};}catch(const SqlFailure& f){reply={Status::DefiniteFailure,job.operation,job.owner,"SQL_"+std::to_string(f.code),f.what(),nullptr};}catch(const std::exception& f){reply={Status::DefiniteFailure,job.operation,job.owner,"EXCEPTION",f.what(),nullptr};}catch(...){reply={Status::DefiniteFailure,job.operation,job.owner,"EXCEPTION","Unknown writer exception",nullptr};}{std::lock_guard<std::mutex> lock(mutex);inFlight=false;if(job.maintenance)maintenance=false;}job.promise.set_value(std::move(reply));
   }
   try{
    hook("before_shutdown_close","");db.close();
    // No SQL, user callback or I/O follows publication on this worker. A final
    // destructor join still provides thread lifetime safety, not a time bound.
    shutdownFinished.store(true,std::memory_order_release);
   }catch(const std::exception& error){std::lock_guard<std::mutex> lock(mutex);shutdownFailure=error.what();if(shutdownFailure.empty())shutdownFailure="Writer-side SQLite close failed";}
    catch(...){std::lock_guard<std::mutex> lock(mutex);shutdownFailure="Unknown writer-side SQLite close failure";}
  });try{future.get();}catch(...){worker.join();throw;}
 }
 void beginShutdown(){{std::lock_guard<std::mutex> lock(mutex);closing=true;}cv.notify_all();}
 ~Impl(){beginShutdown();if(worker.joinable())worker.join();}
 void hook(const std::string& phase,const std::string& op){if(options.diagnosticHook)options.diagnosticHook(phase,op);}
 void open(bool restoring=false,const Value& expected=Value(nullptr),const Value& expectedNode=Value(nullptr),bool allowLaterWrites=false,const std::function<void()>& restoreCheck={}){
  if(!restoring){
   detail::checkRestoreOpen(options.path,options.restoreRecoveryOperation);
   if(!options.restoreRecoveryOperation.empty()){
    need(!options.create,"Recovery-only opening cannot create a profile","RESTORE_OPTIONS");
    pendingRestoreOperation=options.restoreRecoveryOperation;quarantined=true;return;
   }
  }
  need(db.handle==nullptr,"Existing SQLite handle must close before reopening","RESTORE_HANDLE");
  struct stat initialName{};const bool initialExists=lstat(options.path.c_str(),&initialName)==0;
  if(options.create&&!restoring){validateUtc(options.createdUtc);int fd=::open(options.path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);need(fd>=0,"Explicit create refused: profile already exists or cannot be created","CREATE_REFUSED");::close(fd);db.open(options.path.string(),SQLITE_OPEN_READWRITE);db.script("BEGIN IMMEDIATE");try{db.script(profileSchemaSql);db.query("INSERT INTO profile VALUES(1,?,?,?)",{newUuid(),std::string("Fathom.LocalProfile"),options.createdUtc});db.script("COMMIT");}catch(...){try{db.script("ROLLBACK");}catch(...){}throw;}}
  else{
   lease.validateFiles(true);auto before=fileIdentities(options.path);
   bool wal=!field(before,"-wal").null(),shm=!field(before,"-shm").null();
   if(!field(before,"-journal").null()||wal!=shm)throw Failure(Status::DefiniteFailure,"RECOVERY_REQUIRED","Journal or incomplete WAL/SHM pair retained intact; supported recovery is required before opening");
   Database check;check.open(readonlyUri(options.path,!wal&&!shm),SQLITE_OPEN_READONLY|SQLITE_OPEN_URI);
   need(sqlite3_db_config(check.handle,SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,1,nullptr)==SQLITE_OK,"Cannot preserve inspection sidecars");
   if(restoring&&restoreCheck)check.setProgress(restoreCheck);
   inspect(check);
   if(restoring){
    need(initialExists&&field(expectedNode,"device")==Value(std::to_string(initialName.st_dev))&&field(expectedNode,"inode")==Value(std::to_string(initialName.st_ino)),"Restore reopened native identity differs","RESTORE_CHANGED");
    auto actual=restoreBoundary(check,[&]{if(restoreCheck)restoreCheck();lease.validateLeaseIdentity();lease.validateFiles(true);});
    need(allowLaterWrites?(field(actual,"profile_id")==field(expected,"profile_id")&&field(actual,"schema_sha256")==field(expected,"schema_sha256")):actual==expected,
         "Restore reopened authority differs before writer transition","RESTORE_SOURCE_STALE");
   }
   check.close();lease.validateFiles(true);need(fileIdentities(options.path)==before,"Profile changed during exclusive inspection; refuse writer transition","PROFILE_CHANGED");
   db.open(options.path.string(),SQLITE_OPEN_READWRITE);
  }
  db.script("PRAGMA journal_mode=WAL;PRAGMA synchronous=FULL;PRAGMA fullfsync=ON;PRAGMA checkpoint_fullfsync=ON;PRAGMA foreign_keys=ON;PRAGMA busy_timeout=250;PRAGMA wal_autocheckpoint=1000;PRAGMA journal_size_limit=8388608;PRAGMA cache_size=-8192;");lease.validateFiles(true);
  need(lstat(options.path.c_str(),&openedDatabase)==0&&(!initialExists||
       (openedDatabase.st_dev==initialName.st_dev&&openedDatabase.st_ino==initialName.st_ino)),
       "Named profile changed while opening SQLite","PROFILE_CHANGED");
 }
 void restoreNamespace(){
  try{
   lease.validateLeaseIdentity();lease.validateFiles(true);struct stat named{};
   need(lstat(options.path.c_str(),&named)==0&&named.st_dev==openedDatabase.st_dev&&named.st_ino==openedDatabase.st_ino,
        "Named profile differs from the opened SQLite database","RESTORE_SOURCE_CHANGED");
  }catch(const std::exception& e){quarantined=true;throw Failure(Status::Unresolved,"RESTORE_SOURCE_CHANGED",e.what());}
 }
 Value restoreCurrent(const std::function<void()>& extra={}){
  lease.validateLeaseIdentity();lease.validateFiles(true);
  auto check=[&]{if(extra)extra();lease.validateLeaseIdentity();lease.validateFiles(true);};
  if(db.handle){restoreNamespace();return restoreBoundary(db,check);}
  auto before=fileIdentities(options.path);bool wal=!field(before,"-wal").null(),shm=!field(before,"-shm").null();
  need(field(before,"-journal").null()&&wal==shm,"Restore sidecars need explicit recovery; originals retained","RESTORE_SIDECARS");
  Database read;read.open(readonlyUri(options.path,!wal&&!shm),SQLITE_OPEN_READONLY|SQLITE_OPEN_URI);
  need(sqlite3_db_config(read.handle,SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,1,nullptr)==SQLITE_OK,"Cannot preserve restore inspection sidecars");
  auto out=restoreBoundary(read,check);read.close();need(fileIdentities(options.path)==before,"Restore inspection changed source files","RESTORE_CHANGED");return out;
 }
 void restoreClose(const std::string& op,const std::function<void()>& check){
  check();restoreNamespace();need(db.handle!=nullptr,"Restore requires the current database handle","RESTORE_HANDLE");
  int logFrames=-1,checkpointed=-1;int rc=sqlite3_wal_checkpoint_v2(db.handle,nullptr,SQLITE_CHECKPOINT_TRUNCATE,&logFrames,&checkpointed);
  need(rc==SQLITE_OK&&(logFrames==checkpointed),"WAL checkpoint incomplete; preserve all sides and reconcile","RESTORE_CHECKPOINT");
  hook("restore_apply_after_checkpoint",op);check();restoreNamespace();
  db.setProgress(check);
  try{
   need(txt(db.query("PRAGMA journal_mode=DELETE")[0][0])=="delete","Cannot make original standalone; sidecars retained","RESTORE_CHECKPOINT");
   check();db.setProgress({});db.close();check();
  }catch(...){db.setProgress({});throw;}
 }
 void restoreReopen(const Value& expected,const Value& node,bool allowLater,const std::function<void()>& extra){
  lease.validateLeaseIdentity();lease.validateFiles(true);struct stat named{};
  need(lstat(options.path.c_str(),&named)==0&&field(node,"device")==Value(std::to_string(named.st_dev))&&field(node,"inode")==Value(std::to_string(named.st_ino)),
       "Restore normal reopen must retain exact installed native identity","RESTORE_CHANGED");
  if(db.handle){
   auto actual=restoreCurrent(extra);need(allowLater?(field(actual,"profile_id")==field(expected,"profile_id")&&field(actual,"schema_sha256")==field(expected,"schema_sha256")):actual==expected,
        "Restore current authority differs","RESTORE_SOURCE_STALE");return;
  }
  open(true,expected,node,allowLater,extra);
 }
 Reply restoreOperation(const std::string& op,RestoreApplyRequest request,bool reconcileOriginal){
  validateUuid(op);
  if(!request.stopped||request.unresolvedWrites)return {Status::Busy,op,"","QUIESCENCE_REQUIRED","Stop practice and reconcile original writes before restore",nullptr};
  if(quarantined&&(!reconcileOriginal||pendingRestoreOperation!=op))return {Status::Unresolved,op,"","STORE_UNCERTAIN","Only the exact pending restore operation can reconcile this owner",nullptr};
  const Value minimal=Object{{"operation",op},{"live_path",options.path.string()},
      {"directory",(options.path.parent_path()/(".fathom-restore-"+op)).string()},
      {"pending_path",(options.path.parent_path()/".fathom-restore.pending.json").string()},
      {"required_resume_state","stopped"},{"instruction","Retain original operation, exact request and all data; reconcile the recorded operation"}};
  std::unique_ptr<detail::RestoreApplier> apply;
  try{
   need(request.timeout.count()>0&&request.timeout<=std::chrono::seconds(300),"Restore timeout must be positive and at most300seconds","RESTORE_OPTIONS");
   const auto deadline=std::chrono::steady_clock::now()+request.timeout;
   const auto cancelled=request.cancelled;
   auto check=[&]{
    lease.validateLeaseIdentity();lease.validateFiles(true);
    if(cancelled&&cancelled())throw EnvelopeError("RESTORE_CANCELLED","Restore cancelled; preserve original operation");
    need(std::chrono::steady_clock::now()<deadline,"Restore aggregate deadline reached","RESTORE_DEADLINE");
   };
   detail::RestoreOwner owner;
   owner.checkLease=check;
   owner.currentBoundary=[&]{return restoreCurrent(check);};
   owner.checkpointAndClose=[&]{restoreClose(op,check);};
   owner.reopen=[&](const Value& b,const Value& native,bool later){restoreReopen(b,native,later,check);};
   owner.phase=[&](const std::string& phase){hook(phase,op);};
   apply=std::make_unique<detail::RestoreApplier>(op,std::move(request),options.path,std::move(owner));
   auto value=reconcileOriginal?apply->reconcile():apply->apply();
   quarantined=false;pendingRestoreOperation.clear();options.restoreRecoveryOperation.clear();
   const bool installed=field(value,"restore_performed")==Value(true);
   return {installed?Status::Confirmed:Status::DefinitelyAbsent,op,string(field(value,"snapshot"),"profile_id"),installed?"RESTORE_APPLIED":"RESTORE_NOT_APPLIED","",value};
  }catch(const std::exception& error){
   const bool unresolved=quarantined||(apply&&apply->uncertain());
   if(unresolved){quarantined=true;pendingRestoreOperation=op;}
   auto envelope=dynamic_cast<const EnvelopeError*>(&error);auto failure=dynamic_cast<const Failure*>(&error);
   const auto code=envelope?envelope->code:failure?failure->code:std::string("RESTORE_EXCEPTION");
   const bool conflictCode=code=="RESTORE_CONFLICT";
   return {unresolved?Status::Unresolved:conflictCode?Status::Conflict:Status::DefiniteFailure,op,"",code,error.what(),apply?apply->recoveryDetails():minimal};
  }catch(...){
   const bool unresolved=quarantined||(apply&&apply->uncertain());
   if(unresolved){quarantined=true;pendingRestoreOperation=op;}
   return {unresolved?Status::Unresolved:Status::DefiniteFailure,op,"","RESTORE_EXCEPTION","Unknown restore exception; preserve original operation and all data",apply?apply->recoveryDetails():minimal};
  }
 }
 Future submit(std::string op,std::string owner,std::function<Reply()> f,bool checkpoint=false,bool reserveMaintenance=false,bool restoreReconcile=false,bool newAllocation=false){Job job;job.newAllocation=newAllocation;job.maintenance=reserveMaintenance;job.restoreReconcile=restoreReconcile;job.operation=op;job.owner=owner;job.run=std::move(f);if(checkpoint)job.checkpointOwner=owner;auto future=job.promise.get_future();{std::lock_guard<std::mutex> lock(mutex);if(op.empty()||closing||maintenance||(reserveMaintenance&&(inFlight||!queue.empty()))||queue.size()>=64||(checkpoint&&queuedCheckpoints.count(owner))){job.promise.set_value({Status::Busy,op,owner,"QUEUE_REFUSED","Writer busy/maintenance reserved, closing, queue full, or checkpoint already queued",nullptr});return Future(std::move(future),op,owner);}if(checkpoint)queuedCheckpoints.insert(owner);try{queue.push_back(std::move(job));}catch(...){if(checkpoint)queuedCheckpoints.erase(owner);throw;}if(reserveMaintenance)maintenance=true;}cv.notify_one();return Future(std::move(future),op,owner);}
 Reply okay(const std::string& op,const std::string& owner,Value value=nullptr){return {Status::Confirmed,op,owner,"CONFIRMED","",std::move(value)};}
 void admission(){auto wal=options.path.string()+"-wal";std::error_code ec;auto size=std::filesystem::file_size(wal,ec);if(!ec&&size>=64u*1024u*1024u)throw Failure(Status::Busy,"WAL_BACKPRESSURE","WAL reached 64MiB; refuse new activity and request safe stop without deleting history");}
 Reply transaction(const std::string& op,const std::string& owner,const std::function<Value()>& body){
  if(quarantined)return {Status::Unresolved,op,owner,"STORE_UNCERTAIN","Close and reopen for original-key reconciliation before another mutation",nullptr};
  for(int attempt=0;attempt<3;++attempt){bool begun=false,commitStarted=false;try{db.script("BEGIN IMMEDIATE");begun=true;auto data=body();hook("before_commit",op);commitStarted=true;db.script("COMMIT");begun=false;try{hook("after_commit",op);}catch(const std::exception& e){return {Status::Unresolved,op,owner,"ACKNOWLEDGMENT_LOST",e.what(),nullptr};}catch(...){return {Status::Unresolved,op,owner,"ACKNOWLEDGMENT_LOST","Unknown acknowledgment failure after committed transaction",nullptr};}return okay(op,owner,std::move(data));}
   catch(const SqlFailure& e){bool rolledBack=!begun;try{if(begun){db.script("ROLLBACK");rolledBack=true;}}catch(...){}if(commitStarted||!rolledBack||sqlite3_get_autocommit(db.handle)==0){quarantined=true;return {Status::Unresolved,op,owner,"COMMIT_OR_ROLLBACK_UNCERTAIN",e.what(),nullptr};}if((e.code&255)==SQLITE_BUSY&&rolledBack&&attempt<2){std::this_thread::sleep_for(std::chrono::milliseconds(attempt==0?50:150));continue;}if((e.code&255)==SQLITE_BUSY&&rolledBack)return {Status::Busy,op,owner,"SQL_BUSY",e.what(),nullptr};throw;}
   catch(...){if(begun){try{db.script("ROLLBACK");}catch(...){quarantined=true;return {Status::Unresolved,op,owner,"ROLLBACK_UNCERTAIN","Rollback could not be confirmed",nullptr};}}throw;}
  }throw Failure(Status::DefiniteFailure,"RETRY_BUDGET","Unexpected retry exhaustion");
 }
 std::string profile(){return txt(db.query("SELECT profile_id FROM profile")[0][0]);}
 Value receipt(const Row& row){return Object{{"payload",blob(row[0])},{"digest",txt(row[1])},{"committed_seq",num(number(row[2]))}};}
 Reply lookup(const std::string& op,const std::string& owner,const std::string& bytes,bool finalOnly=false){if(quarantined)return {Status::Unresolved,op,owner,"STORE_UNCERTAIN","Reopen before reconciliation",nullptr};auto final=db.query("SELECT payload,digest,committed_seq FROM finalized WHERE owner=?",{owner});if(!final.empty()){conflict(blob(final[0][0])==bytes,"Conflicting original final payload");return okay(op,owner,receipt(final[0]));}if(!finalOnly){auto pending=db.query("SELECT payload,digest FROM pending WHERE owner=?",{owner});if(!pending.empty()){conflict(blob(pending[0][0])==bytes,"Conflicting original pending payload");return {Status::Unresolved,op,owner,"PENDING","Original outcome is durably pending",Object{{"payload",bytes},{"digest",txt(pending[0][1])}}};}}return {Status::DefinitelyAbsent,op,owner,"ABSENT","No matching final receipt",nullptr};}
};
ProfileStore::ProfileStore(StoreOptions o):impl_(std::make_unique<Impl>(std::move(o))){}
ProfileStore::~ProfileStore()=default;
void ProfileStore::beginShutdown(){impl_->beginShutdown();}
bool ProfileStore::shutdownComplete()const noexcept{return impl_->shutdownFinished.load(std::memory_order_acquire);}
std::string ProfileStore::shutdownError()const{std::lock_guard<std::mutex> lock(impl_->mutex);return impl_->shutdownFailure;}
std::string ProfileStore::schemaIdentity(){return content::sha256(profileSchemaSql);}
std::string ProfileStore::legacySchemaIdentity(){return content::sha256(profileSchemaV1Sql);}
Reply ProfileStore::waitForAcknowledgment(Future& future){if(future.wait_for(std::chrono::seconds(1))==std::future_status::ready)return future.get();return {Status::Unresolved,future.operationId(),future.ownerId(),"ACK_TIMEOUT","Original operation continues; retain key and bytes, then reconcile",nullptr};}
ProfileStore::Future ProfileStore::createSession(std::string op,std::string at,std::string zone,std::optional<std::int64_t> planned,Value plan){auto* p=impl_.get();return p->submit(op,"",[=]{validateUtc(at);localDay(at,zone);need(!planned||(*planned>0&&*planned<=14400),"Session budget outside 1..14400");need(plan.null()||parseCanonical(canonical(plan)).isObject(),"Session plan must be object or absent");p->admission();std::string key;auto reply=p->transaction(op,"",[&]{key=fresh(p->db);p->db.query("INSERT INTO session VALUES(?,?,?,?,?)",{key,at,zone,planned?Cell(*planned):Cell(nullptr),plan.null()?Cell(nullptr):Cell(Blob{canonical(plan)})});return Object{{"session_id",key}};});if(!key.empty())reply.owner=key;return reply;});}
ProfileStore::Future ProfileStore::createSessionWithIdentity(std::string op,std::string owner,std::string at,std::string zone,std::int64_t planned,Value plan){return createSessionWithIdentity(std::move(op),std::move(owner),std::move(at),std::move(zone),std::optional<std::int64_t>{planned},std::move(plan));}
ProfileStore::Future ProfileStore::createSessionWithIdentity(std::string op,std::string owner,std::string at,std::string zone,std::optional<std::int64_t> planned,Value plan){
 auto* p=impl_.get();return p->submit(op,"",[=]{
  validateUuid(owner);validateUtc(at);localDay(at,zone);need(!planned||(*planned>0&&*planned<=14400),"Session budget outside 1..14400");
  need(plan.isObject()&&plan.find("original_start_operation")&&*plan.find("original_start_operation")==Value(op)
       &&plan.find("original_session_id")&&*plan.find("original_session_id")==Value(owner),"Session plan must bind its exact original operation and owner");
  // The retained operation is unique across Session owners, not merely within one row.
  const auto bindings=p->db.query("SELECT session_id FROM session WHERE plan_ref IS NOT NULL AND json_extract(CAST(plan_ref AS TEXT),'$.original_start_operation')=? LIMIT 2",{op});
  conflict(bindings.empty()||bindings==Rows{{owner}},"Original Session operation is already bound to another owner");
  const auto bytes=canonical(plan);const auto existing=p->db.query("SELECT session_id,started_utc,timezone,planned_seconds,plan_ref FROM session WHERE session_id=?",{owner});
  if(!existing.empty()){
   conflict(existing==Rows{{owner,at,zone,planned?Cell(*planned):Cell(nullptr),Blob{bytes}}},"Conflicting original Session request");
   conflict(p->db.query("SELECT session_id FROM session_close WHERE session_id=?",{owner}).empty(),"Original Session is already closed");
   return p->okay(op,owner,Object{{"session_id",owner},{"original_request_adopted",true}});
  }
  p->admission();auto reply=p->transaction(op,owner,[&]{uniqueAvailable(p->db,owner);p->db.query("INSERT INTO session VALUES(?,?,?,?,?)",{owner,at,zone,planned?Cell(*planned):Cell(nullptr),Blob{bytes}});return Object{{"session_id",owner}};});
  // A returned identity is not a success claim: ambiguous/failed status remains.
  reply.owner=owner;return reply;
 });
}
ProfileStore::Future ProfileStore::closeSession(std::string op,std::string owner,std::string at,std::string outcome){auto* p=impl_.get();return p->submit(op,owner,[=]{validateUuid(owner);validateUtc(at);need(std::set<std::string>{"complete","partial","interrupted","cancelled"}.count(outcome),"Session outcome");return p->transaction(op,owner,[&]{auto start=p->db.query("SELECT started_utc FROM session WHERE session_id=?",{owner});need(start.size()==1&&!utcBefore(at,txt(start[0][0])),"Session missing or close precedes start");auto old=p->db.query("SELECT ended_utc,outcome FROM session_close WHERE session_id=?",{owner});if(!old.empty())conflict(old==Rows{{at,outcome}},"Conflicting Session close");else p->db.query("INSERT INTO session_close VALUES(?,?,?)",{owner,at,outcome});return Value(Object{{"session_id",owner},{"ended_utc",at},{"outcome",outcome}});});});}
ProfileStore::Future ProfileStore::allocate(std::string op,std::string kind,Value c,std::string at){auto* p=impl_.get();return p->submit(op,"",[=]{
 validateContext(c,kind);validateUtc(at);p->admission();std::string key,blockingOwner;
 try{
  auto reply=p->transaction(op,"",[&]{
   auto prior=p->db.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE f.owner IS NULL LIMIT 1");
   if(!prior.empty()){blockingOwner=txt(prior[0][0]);throw Failure(Status::Unresolved,"UNRESOLVED_ACTIVITY","Resolve and confirm the original activity before another allocation");}
   key=fresh(p->db);p->db.query("INSERT INTO identity VALUES(?,?,?,?,?)",{key,kind,kind=="Attempt"?Cell(string(c,"session_id")):Cell(nullptr),at,Blob{canonical(c)}});return Object{{"owner",key},{"kind",kind},{"context",c}};
  });if(!key.empty())reply.owner=key;return reply;
 }catch(const Failure& failure){
  // Only this pre-INSERT refusal, after a completed rollback, proves this NEW
  // operation admitted no identity. The older owner remains unresolved.
  if(failure.code!="UNRESOLVED_ACTIVITY"||!key.empty()||blockingOwner.empty()||p->quarantined||sqlite3_get_autocommit(p->db.handle)==0)throw;
  validateUuid(blockingOwner);
  return Reply{Status::DefiniteFailure,op,"","ALLOCATION_REFUSED_PRIOR_ACTIVITY","No new activity was allocated. Return to Home. Keep this profile and its original recovery records; the earlier unfinished activity must be recovered before another Start.",Object{{"version","allocation-refusal.1"},{"new_allocation","not_admitted"},{"rollback_confirmed",true},{"blocking_owner",blockingOwner}}};
 }
},false,false,false,true);}
ProfileStore::Future ProfileStore::seal(std::string op,std::string owner,std::string bytes){auto* p=impl_.get();return p->submit(op,owner,[=]{auto e=validateEnvelope(bytes);need(e.owner==owner,"Seal owner mismatch");bind(p->db,e);auto old=p->lookup(op,owner,bytes);if(old.status==Status::Confirmed)return old;if(old.status==Status::Unresolved&&old.code=="PENDING")return p->okay(op,owner,Object{{"pending",true},{"digest",e.digest}});return p->transaction(op,owner,[&]{p->db.query("INSERT INTO pending VALUES(?,?,?,?)",{owner,std::int64_t(1),Blob{bytes},e.digest});return Object{{"pending",true},{"digest",e.digest}};});});}
ProfileStore::Future ProfileStore::commit(std::string op,std::string owner,std::string bytes){auto* p=impl_.get();return p->submit(op,owner,[=]{auto e=validateEnvelope(bytes);need(e.owner==owner,"Commit owner mismatch");bind(p->db,e);auto old=p->lookup(op,owner,bytes);if(old.status==Status::Confirmed)return old;need(old.status==Status::Unresolved,"Seal original outcome before commit","PENDING_REQUIRED");return p->transaction(op,owner,[&]{auto seq=advance(p->db);p->db.query("INSERT INTO finalized VALUES(?,?,?,?,?,?,?,?,?,?,?)",{owner,Blob{bytes},e.digest,seq,e.practiceUtc,e.timezone,e.day,std::to_string(e.active.numerator()),std::to_string(e.active.denominator()),e.outcome,e.assessment?Cell(*e.assessment):Cell(nullptr)});p->db.query("DELETE FROM pending WHERE owner=?",{owner});p->db.query("DELETE FROM checkpoint WHERE owner=?",{owner});return Object{{"payload",bytes},{"digest",e.digest},{"committed_seq",num(seq)}};});});}
ProfileStore::Future ProfileStore::reconcile(std::string op,std::string owner,std::string bytes){auto* p=impl_.get();return p->submit(op,owner,[=]{auto e=validateEnvelope(bytes);need(e.owner==owner,"Reconciliation owner mismatch");bind(p->db,e);return p->lookup(op,owner,bytes);});}
ProfileStore::Future ProfileStore::checkpoint(std::string op,std::string owner,std::int64_t gen,std::int64_t seq,std::string bytes){auto* p=impl_.get();return p->submit(op,owner,[=]{auto a=allocation(p->db,owner);validateCheckpoint(owner,gen,seq,bytes,a.first,a.second);return p->transaction(op,owner,[&]{p->db.query("INSERT INTO checkpoint VALUES(?,?,?,?) ON CONFLICT(owner) DO UPDATE SET generation=excluded.generation,sequence=excluded.sequence,payload=excluded.payload",{owner,gen,seq,Blob{bytes}});return Object{{"generation",num(gen)},{"sequence",num(seq)},{"stopped_on_reopen",true}};});},true);}
ProfileStore::Future ProfileStore::recoveryState(std::string op,std::string owner){auto* p=impl_.get();return p->submit(op,owner,[=]{validateUuid(owner);auto a=allocation(p->db,owner);auto final=p->db.query("SELECT payload,digest,committed_seq FROM finalized WHERE owner=?",{owner});if(!final.empty()){auto data=p->receipt(final[0]);data.object()["state"]="final";data.object()["stopped_on_reopen"]=true;return p->okay(op,owner,data);}auto pending=p->db.query("SELECT payload,digest FROM pending WHERE owner=?",{owner});if(!pending.empty())return p->okay(op,owner,Object{{"state","pending"},{"payload",blob(pending[0][0])},{"digest",txt(pending[0][1])},{"stopped_on_reopen",true}});auto checkpoint=p->db.query("SELECT generation,sequence,payload FROM checkpoint WHERE owner=?",{owner});if(!checkpoint.empty())return p->okay(op,owner,Object{{"state","checkpoint"},{"generation",num(number(checkpoint[0][0]))},{"sequence",num(number(checkpoint[0][1]))},{"payload",blob(checkpoint[0][2])},{"stopped_on_reopen",true}});return p->okay(op,owner,Object{{"state","allocated"},{"kind",a.first},{"context",a.second},{"stopped_on_reopen",true}});});}
namespace {
Value pendingSuiteMembers(Database& db,const Value& view,const std::string& at){
 Array out;if(field(view,"closed")==Value(true))return out;auto sid=string(view,"suite_id");std::set<std::string> known,sourceKeys;for(auto& m:field(view,"members").array()){known.insert(string(m,"attempt_id"));sourceKeys.insert(string(m,"source_exercise_key"));}
 db.visit("SELECT f.payload,s.plan_ref FROM finalized f JOIN identity i ON i.owner=f.owner JOIN session s ON s.session_id=i.session_id WHERE i.kind='Attempt' ORDER BY f.committed_seq",[&](const Row& row){if(null(row[1]))return;auto ref=parseCanonical(blob(row[1]));auto id=ref.find("suite_id");if(!id||*id!=Value(sid))return;auto e=validateEnvelope(blob(row[0]));if(known.count(e.owner))return;auto& result=field(e.value,"result");if(e.outcome!="complete"||field(result,"outcome")!=Value("natural")||e.active.numerator()<=0||!field(result,"assessment").null())return;auto& item=suite::matchingItem(field(view,"plan"),e);conflict(sourceKeys.insert(string(item,"source_exercise_key")).second,"Multiple actual Attempts for same suite exercise require explicit reconciliation");out.emplace_back(Object{{"suite_id",sid},{"attempt_id",e.owner},{"completed_utc",at.empty()?Value(nullptr):Value(at)},{"context",field(e.value,"context")},{"envelope_sha256",e.digest},{"source_exercise_key",field(item,"source_exercise_key")}});});return out;
}
Value suiteView(Database& db,const std::string& id){
 auto projection=suite::projection(state(db,true));auto& views=field(projection,"suites");auto found=views.find(id);need(found,"Unknown suite","SUITE_ABSENT");return *found;
}
std::optional<Value> suiteReplay(Database& db,const std::string& op,const std::string& sid,const std::string& kind,const std::string& bytes){
 auto rows=db.query("SELECT suite_id,kind,payload,fact_id,committed_seq FROM suite_fact WHERE operation_id=?",{op});if(rows.empty())return {};auto& r=rows[0];conflict(txt(r[0])==sid&&txt(r[1])==kind&&blob(r[2])==bytes,"Changed suite operation payload");return Object{{"fact_id",txt(r[3])},{"committed_seq",num(number(r[4]))},{"replayed",true},{"suite",suiteView(db,sid)}};
}
Value insertSuiteFact(Database& db,const std::string& op,const std::string& sid,const std::string& kind,const std::string& at,const Value& payload,const std::string& id){
 nonempty(op);auto bytes=canonical(payload);uniqueAvailable(db,id);auto seq=advance(db);db.query("INSERT INTO suite_fact VALUES(?,?,?,?,?,?,?,?)",{id,sid,kind,op,at,Blob{bytes},content::sha256(bytes),seq});return Object{{"fact_id",id},{"committed_seq",num(seq)},{"replayed",false},{"suite",suiteView(db,sid)}};
}
std::filesystem::path preserveSuiteMigration(Database& db,const std::filesystem::path& original,const std::string& op){
 inspect(db);need(schemaVersion(db)==1,"Migration requires exact schema1");need(db.query("SELECT owner FROM pending LIMIT 1").empty()&&db.query("SELECT owner FROM checkpoint LIMIT 1").empty()&&db.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON i.owner=f.owner WHERE f.owner IS NULL LIMIT 1").empty(),"Reconcile all original activities before suite migration","MIGRATION_QUIESCENCE");
 auto path=original.parent_path()/("suite-schema1-preserved-"+content::sha256(op)+"-"+newUuid()+".sqlite");int fd=::open(path.c_str(),O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR|O_CLOEXEC,0600);need(fd>=0,"Cannot retain pre-migration backup","MIGRATION_BACKUP");::close(fd);
 Database copy;copy.open(path.string(),SQLITE_OPEN_READWRITE);auto* backup=sqlite3_backup_init(copy.handle,"main",db.handle,"main");need(backup,"Cannot initialize retained migration backup","MIGRATION_BACKUP");int rc=SQLITE_OK;auto end=std::chrono::steady_clock::now()+std::chrono::seconds(30);
 do{rc=sqlite3_backup_step(backup,256);}while(rc==SQLITE_OK&&std::chrono::steady_clock::now()<end);int finish=sqlite3_backup_finish(backup);need(rc==SQLITE_DONE&&finish==SQLITE_OK,"Migration backup incomplete; original unchanged","MIGRATION_BACKUP");copy.script("PRAGMA journal_mode=DELETE;PRAGMA synchronous=FULL;");need(txt(copy.query("PRAGMA journal_mode")[0][0])=="delete","Retained migration backup must be standalone");inspect(copy);need(schemaVersion(copy)==1&&state(copy,true)==state(db,true),"Migration backup authority/schema mismatch","MIGRATION_BACKUP");copy.close();for(auto suffix:{"-wal","-shm","-journal"}){struct stat sidecar{};need(lstat((path.string()+suffix).c_str(),&sidecar)!=0&&errno==ENOENT,"Migration backup still requires sidecar");}fd=::open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC);need(fd>=0,"Cannot sync retained migration backup");int sync=::fsync(fd);::close(fd);need(sync==0,"Cannot persist migration backup");fd=::open(original.parent_path().c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);need(fd>=0,"Cannot sync migration backup directory");sync=::fsync(fd);::close(fd);need(sync==0,"Cannot persist migration backup name");return path;
}
}
ProfileStore::Future ProfileStore::beginSuite(std::string op,std::string sid,std::string at,Value plan){auto* p=impl_.get();return p->submit(op,sid,[=]{validateUuid(sid);validateUtc(at);suite::plan(plan);nonempty(op);Object payload{{"suite_id",sid},{"created_utc",at},{"plan",plan}};std::optional<std::filesystem::path> backup;Value original;
 if(schemaVersion(p->db)==1){backup=preserveSuiteMigration(p->db,p->options.path,op);original=state(p->db,true);}
 return p->transaction(op,sid,[&]{if(schemaVersion(p->db)==1){p->db.script(suiteSchemaMigrationSql);auto after=state(p->db,true);after.object().erase("suite_fact");for(auto& row:after.object().at("metadata").array())if(row.array()[0]==Value("data_schema_version"))row.array()[1]="1";need(after==original,"Migration changed original13 authorities");inspect(p->db);}
 if(auto old=suiteReplay(p->db,op,sid,"definition",canonical(payload)))return *old;
 conflict(p->db.query("SELECT fact_id FROM suite_fact WHERE suite_id=? AND kind='definition'",{sid}).empty(),"Suite already exists under another operation");auto result=insertSuiteFact(p->db,op,sid,"definition",at,payload,sid);if(backup)result.object().emplace("retained_schema1_backup",backup->string());return result;});},false,true);}
ProfileStore::Future ProfileStore::appendSuiteMember(std::string op,std::string sid,std::string owner,std::string at){auto* p=impl_.get();return p->submit(op,sid,[=]{validateUuid(sid);validateUuid(owner);validateUtc(at);need(schemaVersion(p->db)==2,"Suite definition required");auto view=suiteView(p->db,sid);auto rows=p->db.query("SELECT payload FROM finalized WHERE owner=?",{owner});need(rows.size()==1,"Suite member is not confirmed finalized");auto e=validateEnvelope(blob(rows[0][0]));auto& item=suite::matchingItem(field(view,"plan"),e);need(!utcBefore(at,e.practiceUtc),"Suite member time precedes original practice");auto session=p->db.query("SELECT plan_ref FROM session WHERE session_id=?",{string(field(e.value,"context"),"session_id")});need(session.size()==1&&!null(session[0][0])&&field(parseCanonical(blob(session[0][0])),"suite_id")==Value(sid),"Attempt Session does not belong to suite");Object payload{{"suite_id",sid},{"attempt_id",owner},{"completed_utc",at},{"context",field(e.value,"context")},{"envelope_sha256",e.digest},{"source_exercise_key",field(item,"source_exercise_key")}};
 return p->transaction(op,sid,[&]{if(auto old=suiteReplay(p->db,op,sid,"member",canonical(payload)))return *old;conflict(field(view,"closed")==Value(false),"Suite review already froze membership");auto all=suite::projection(state(p->db,true));for(auto& kv:field(all,"suites").object())for(auto& m:field(kv.second,"members").array())conflict(field(m,"attempt_id")!=Value(owner),"Attempt already belongs to a suite");for(auto& m:field(view,"members").array())conflict(field(m,"source_exercise_key")!=field(item,"source_exercise_key"),"Suite exercise already has another Attempt");return insertSuiteFact(p->db,op,sid,"member",at,payload,fresh(p->db));});});}
ProfileStore::Future ProfileStore::readSuite(std::string op,std::string sid){auto* p=impl_.get();return p->submit(op,sid,[=]{if(schemaVersion(p->db)==1)return Reply{Status::DefinitelyAbsent,op,sid,"SUITE_ABSENT","No suite definition",nullptr};inspect(p->db);auto projection=suite::projection(state(p->db,true));auto& views=field(projection,"suites");if(!sid.empty()){validateUuid(sid);auto view=views.find(sid);if(!view)return Reply{Status::DefinitelyAbsent,op,sid,"SUITE_ABSENT","No matching suite",nullptr};auto result=*view;result.object().emplace("pending_members",pendingSuiteMembers(p->db,result,""));return p->okay(op,sid,result);}const Value* found=nullptr;for(auto& kv:views.object())if(field(kv.second,"closed")==Value(false)){conflict(!found,"Multiple pending suites; explicit selection required");found=&kv.second;}if(!found)return Reply{Status::DefinitelyAbsent,op,sid,"SUITE_ABSENT","No pending suite",nullptr};auto result=*found;result.object().emplace("pending_members",pendingSuiteMembers(p->db,result,""));return p->okay(op,string(*found,"suite_id"),result);});}
ProfileStore::Future ProfileStore::submitSuiteReview(std::string op,std::string sid,std::string at,Value score){auto* p=impl_.get();return p->submit(op,sid,[=]{validateUuid(sid);validateUtc(at);suite::score(score);need(schemaVersion(p->db)==2,"Suite definition required");
 return p->transaction(op,sid,[&]{auto view=suiteView(p->db,sid);if(field(view,"closed")==Value(false)){auto pending=pendingSuiteMembers(p->db,view,at);for(auto& m:pending.array()){auto recoveredOp=op+"/recovered/"+string(m,"attempt_id");insertSuiteFact(p->db,recoveredOp,sid,"member",at,m,fresh(p->db));}view=suiteView(p->db,sid);}Array members;for(auto& m:field(view,"members").array()){members.emplace_back(field(m,"attempt_id"));need(!utcBefore(at,string(m,"completed_utc")),"Review predates member registration");}need(!members.empty()||score.null(),"Cannot score empty suite");std::sort(members.begin(),members.end(),[](const Value& x,const Value& y){return x.string()<y.string();});auto disposition=members.empty()?"unplayed_closed_without_assessment":score.null()?"closed_without_assessment":"shared_suite_self_assessment";Object payload{{"suite_id",sid},{"reviewed_utc",at},{"score",score},{"members",members},{"disposition",disposition}};if(auto old=suiteReplay(p->db,op,sid,"review",canonical(payload)))return *old;conflict(field(view,"closed")==Value(false),"Suite review already exists under another operation");return insertSuiteFact(p->db,op,sid,"review",at,payload,fresh(p->db));});});}
ProfileStore::Future ProfileStore::appendLate(std::string op,std::string owner,std::string event,std::string at,std::string bytes){auto* p=impl_.get();return p->submit(op,owner,[=]{validateUuid(owner);validateUuid(event);validateUtc(at);auto v=parseCanonical(bytes);need(string(v,"original_owner")==owner,"Late evidence original owner mismatch");integer(field(v,"generation"));allocation(p->db,owner);return p->transaction(op,owner,[&]{auto old=p->db.query("SELECT owner,received_utc,payload,digest FROM late_evidence WHERE event_key=?",{event});Row expected{owner,at,Blob{bytes},content::sha256(bytes)};if(!old.empty())conflict(old==Rows{expected},"Conflicting late fact");else{uniqueAvailable(p->db,event);p->db.query("INSERT INTO late_evidence VALUES(?,?,?,?,?)",{event,owner,at,Blob{bytes},content::sha256(bytes)});}return Object{{"event_key",event}};});});}
ProfileStore::Future ProfileStore::acknowledge(std::string op,std::string fact,std::string item,std::int64_t revision,std::string at){auto* p=impl_.get();return p->submit(op,fact,[=]{validateUuid(fact);itemId(item);need(revision>0,"Content revision");validateUtc(at);return p->transaction(op,fact,[&]{auto old=p->db.query("SELECT item_id,content_revision,acknowledged_utc,committed_seq FROM acknowledgment WHERE fact_id=?",{fact});std::int64_t seq;if(!old.empty()){conflict(txt(old[0][0])==item&&number(old[0][1])==revision&&txt(old[0][2])==at,"Conflicting acknowledgment");seq=number(old[0][3]);}else{uniqueAvailable(p->db,fact);seq=advance(p->db);p->db.query("INSERT INTO acknowledgment VALUES(?,?,?,?,?)",{fact,item,revision,at,seq});}return Object{{"fact_id",fact},{"committed_seq",num(seq)}};});});}
ProfileStore::Future ProfileStore::attest(std::string op,std::string bytes){auto* p=impl_.get();std::string fact;try{fact=string(parseCanonical(bytes),"fact_id");}catch(...){}return p->submit(op,fact,[=]{auto v=parseCanonical(bytes);auto id=string(v,"fact_id");validateAttestation(v,p->profile(),linkedContext(p->db,v));auto old=p->db.query("SELECT payload,committed_seq FROM source_attestation WHERE fact_id=?",{id});if(!old.empty()){conflict(blob(old[0][0])==bytes,"Conflicting source fact");return p->okay(op,id,Object{{"fact_id",id},{"committed_seq",num(number(old[0][1]))}});}if(!p->options.sourceValidator||!p->options.sourceValidator(v))throw Failure(Status::Unsupported,"SOURCE_SEMANTICS","No supported source authority/semantic validator accepted this new fact");return p->transaction(op,id,[&]{uniqueAvailable(p->db,id);auto seq=advance(p->db);p->db.query("INSERT INTO source_attestation VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",{id,field(v,"owner").null()?Cell(nullptr):Cell(string(v,"owner")),string(v,"item_id"),integer(field(v,"content_revision"),1),Blob{canonical(field(v,"rubric_ref"))},Blob{canonical(field(v,"context"))},string(v,"take_id"),string(v,"work_id"),string(v,"performer_ref"),string(v,"practice_utc"),string(v,"timezone"),string(v,"local_day"),Blob{bytes},content::sha256(bytes),seq});return Object{{"fact_id",id},{"committed_seq",num(seq)}};});});}
ProfileStore::Future ProfileStore::readProfileIdentity(std::string op){auto* p=impl_.get();return p->submit(op,"",[=]{if(p->quarantined)throw Failure(Status::Unresolved,"STORE_UNCERTAIN","Reopen before profile identity reconciliation");auto id=p->profile();Object data{{"profile_id",id}};const auto named=p->db.query("SELECT namespace_version,value_bytes FROM preferences WHERE key=?",{std::string(profile_names::key)});if(!named.empty()){const auto identity=parseCanonical(blob(named[0][1]));need(number(named[0][0])==1&&profile_names::valid(identity)&&identity.object().at("profile_id")==Value(id),"Profile name metadata does not match its original UUID");data.emplace("profile_name",identity.object().at("display_name"));}return p->okay(op,id,std::move(data));});}
ProfileStore::Future ProfileStore::readPreferenceKeys(std::string op,std::string prefix,std::string after,std::int64_t limit){auto* p=impl_.get();return p->submit(op,prefix,[=]{need(!prefix.empty()&&prefix.size()<=4096&&after.size()<=4096&&limit>0&&limit<=512&&(after.empty()||after.rfind(prefix,0)==0),"Bounded preference key cursor");if(p->quarantined)throw Failure(Status::Unresolved,"STORE_UNCERTAIN","Reopen before preference discovery");auto rows=p->db.query("SELECT key FROM preferences WHERE substr(key,1,length(?))=? AND key>? ORDER BY key LIMIT ?",{prefix,prefix,after,limit+1});Value::Array keys;for(std::size_t i=0;i<rows.size()&&i<static_cast<std::size_t>(limit);++i)keys.emplace_back(txt(rows[i][0]));return p->okay(op,p->profile(),Object{{"profile_id",p->profile()},{"keys",std::move(keys)},{"has_more",rows.size()>static_cast<std::size_t>(limit)}});});}
ProfileStore::Future ProfileStore::readPreferences(std::string op,std::string key){auto* p=impl_.get();return p->submit(op,key,[=]{nonempty(key);auto rows=p->db.query("SELECT namespace_version,revision,value_bytes FROM preferences WHERE key=?",{key});if(rows.empty())return Reply{Status::DefinitelyAbsent,op,key,"ABSENT","No preference namespace",nullptr};auto version=number(rows[0][0]),revision=number(rows[0][1]);auto bytes=blob(rows[0][2]);auto v=parseCanonical(bytes);bool supported=false;try{supported=p->options.preferenceValidator&&p->options.preferenceValidator(key,version,v);}catch(...){supported=false;}return p->okay(op,key,Object{{"namespace_version",num(version)},{"revision",num(revision)},{"bytes",bytes},{"applicable",supported}});});}
ProfileStore::Future ProfileStore::compareExchangePreferences(std::string op,std::string key,std::int64_t version,std::int64_t expected,std::string bytes,bool stopped){auto* p=impl_.get();return p->submit(op,key,[=]{nonempty(key);need(version>0&&expected>=0&&expected<std::numeric_limits<std::int64_t>::max(),"Preference revision/version");need(stopped,"Apply settings only while explicitly stopped","STOP_REQUIRED");auto v=parseCanonical(bytes);need(v.isObject(),"Preference object");if(!p->options.preferenceValidator||!p->options.preferenceValidator(key,version,v))throw Failure(Status::Unsupported,"PREFERENCE_SEMANTICS","Unknown or invalid preference namespace/version");return p->transaction(op,key,[&]{auto old=p->db.query("SELECT namespace_version,revision FROM preferences WHERE key=?",{key});if(old.empty()){conflict(expected==0,"Preference missing at expected revision");p->db.query("INSERT INTO preferences VALUES(?,?,?,?)",{key,version,std::int64_t(1),Blob{bytes}});}else{conflict(number(old[0][1])==expected,"Stale preference revision");if(number(old[0][0])!=version)throw Failure(Status::Unsupported,"PREFERENCE_MIGRATION","Namespace change requires supported migration");p->db.query("UPDATE preferences SET revision=?,value_bytes=? WHERE key=?",{expected+1,Blob{bytes},key});}return Object{{"revision",num(expected+1)},{"namespace_version",num(version)}};});});}
ProfileStore::Future ProfileStore::writeCache(std::string op,std::string key,std::int64_t m,std::string eh,std::string ch,std::string rule,std::string at,std::string bytes){auto* p=impl_.get();return p->submit(op,key,[=]{nonempty(key);digest(eh);digest(ch);nonempty(rule);validateUtc(at);need(m>=0&&parseCanonical(bytes).isObject(),"Invalid cache payload");need(bytes.size()<=16u*1024u*1024u,"Disposable cache exceeds 16MiB");return p->transaction(op,key,[&]{conflict(marker(p->db)==m&&stateHash(p->db,false)==eh,"Stale cache evidence");auto size=scalar(p->db,"SELECT coalesce(sum(length(value_bytes)),0) FROM projection_cache");auto old=p->db.query("SELECT length(value_bytes) FROM projection_cache WHERE cache_key=?",{key});if(!old.empty())size-=number(old[0][0]);if(size>16*1024*1024-static_cast<std::int64_t>(bytes.size()))p->db.query("DELETE FROM projection_cache");p->db.query("INSERT INTO projection_cache VALUES(?,?,?,?,?,?,?) ON CONFLICT(cache_key) DO UPDATE SET evidence_marker=excluded.evidence_marker,evidence_sha256=excluded.evidence_sha256,content_selection_sha256=excluded.content_selection_sha256,rule_version=excluded.rule_version,as_of_utc=excluded.as_of_utc,value_bytes=excluded.value_bytes",{key,m,eh,ch,rule,at,Blob{bytes}});return Object{{"stored",true}};});});}
ProfileStore::Future ProfileStore::readCache(std::string op,std::string key,std::string ch,std::string rule,std::string at){auto* p=impl_.get();return p->submit(op,key,[=]{nonempty(key);digest(ch);nonempty(rule);validateUtc(at);auto rows=p->db.query("SELECT evidence_marker,evidence_sha256,content_selection_sha256,rule_version,as_of_utc,value_bytes FROM projection_cache WHERE cache_key=?",{key});inspect(p->db);auto authoritativeMarker=marker(p->db);auto authoritativeHash=stateHash(p->db,false);bool current=false;std::string bytes;if(!rows.empty())try{const auto& r=rows[0];bytes=blob(r[5]);current=number(r[0])==authoritativeMarker&&txt(r[1])==authoritativeHash&&txt(r[2])==ch&&txt(r[3])==rule&&txt(r[4])==at&&bytes.size()<=16u*1024u*1024u&&parseCanonical(bytes).isObject();}catch(const std::exception&){current=false;}if(!current)return Reply{Status::DefinitelyAbsent,op,key,"CACHE_MISS","Missing, stale or malformed disposable cache; recompute from authoritative history",nullptr};return p->okay(op,key,Object{{"bytes",bytes}});});}
ProfileStore::Future ProfileStore::observeRule(std::string op,std::string fact,Value config,Value selection,Value displayed,std::string at){auto* p=impl_.get();return p->submit(op,fact,[=]{validateUuid(fact);validateUtc(at);need(parseCanonical(canonical(config)).isObject()&&parseCanonical(canonical(selection)).isObject()&&parseCanonical(canonical(displayed)).isObject(),"Rule observation objects");auto cb=canonical(config),sb=canonical(selection),db=canonical(displayed),version=string(config,"version");return p->transaction(op,fact,[&]{auto old=p->db.query("SELECT rule_version,rule_config,content_selection,as_of_utc,displayed_state FROM rule_observation WHERE fact_id=?",{fact});if(!old.empty()){conflict(old==Rows{{version,Blob{cb},Blob{sb},at,Blob{db}}},"Conflicting rule observation");return Value(Object{{"fact_id",fact}});}uniqueAvailable(p->db,fact);auto m=marker(p->db);auto eh=stateHash(p->db,false);Value record=Object{{"fact_id",fact},{"rule_version",version},{"rule_config",cb},{"rule_config_sha256",content::sha256(cb)},{"evidence_marker",num(m)},{"evidence_sha256",eh},{"content_selection",sb},{"content_selection_sha256",content::sha256(sb)},{"as_of_utc",at},{"displayed_state",db},{"displayed_state_sha256",content::sha256(db)}};validateRuleObservation(record);p->db.query("INSERT INTO rule_observation VALUES(?,?,?,?,?,?,?,?,?,?,?)",{fact,version,Blob{cb},content::sha256(cb),m,eh,Blob{sb},content::sha256(sb),at,Blob{db},content::sha256(db)});return Value(record);});});}
ProfileStore::Future ProfileStore::applyRestore(std::string op,RestoreApplyRequest request){auto* p=impl_.get();
    return p->submit(op,"",[=]{return p->restoreOperation(op,request,false);},false,true);
}
ProfileStore::Future ProfileStore::reconcileRestore(std::string op,RestoreApplyRequest request){auto* p=impl_.get();
    return p->submit(op,"",[=]{return p->restoreOperation(op,request,true);},false,true,true);
}
ProfileStore::Future ProfileStore::prepareRestore(std::string op,BackupSnapshotOptions options,RestorePreparationRequest request){
    options.includeArchiveManifest=true;options.includeArchiveContainer=true;
    options.restorePreparation=std::move(request);
    return prepareBackupSnapshot(std::move(op),std::move(options));
}
ProfileStore::Future ProfileStore::prepareBackupSnapshot(std::string op,BackupSnapshotOptions options){
    auto* p=impl_.get();
    const auto started=std::chrono::steady_clock::now();
    return p->submit(op,"",[=]{
        if(!options.stopped||options.unresolvedWrites)
            throw Failure(Status::Busy,"QUIESCENCE_REQUIRED","Stop practice and reconcile original outstanding writes before a backup snapshot");
        need(options.timeout.count()>0&&options.timeout<=std::chrono::seconds(300),"Snapshot timeout must be positive and at most the accepted300seconds");
        need(!options.includeArchiveContainer||options.includeArchiveManifest,"Archive container requires a verified manifest stage","ARCHIVE_MANIFEST_REQUIRED");
        need(!options.publication||options.includeArchiveContainer,"Publication requires a verified archive container","PUBLICATION_CONTAINER_REQUIRED");
        need(!options.restorePreparation||(options.includeArchiveContainer&&!options.publication),"Restore preparation requires original archive and excludes publication","RESTORE_OPTIONS");
        if(options.restorePreparation)validateUuid(op);
        const auto end=started+options.timeout;
        auto check=[&]{
            if(options.restorePreparation)p->restoreNamespace();
            if(options.cancelled&&options.cancelled())throw Failure(Status::DefiniteFailure,"SNAPSHOT_CANCELLED","Snapshot cancelled; source retained and no backup archive published");
            if(std::chrono::steady_clock::now()>=end)throw Failure(Status::DefiniteFailure,"SNAPSHOT_DEADLINE","Snapshot deadline reached; source retained and no backup archive published");
        };
        check();
        SnapshotProgress sourceProgress(p->db,check);
        bool restoreStageCreated=false;
        struct stat restoreStageIdentity{};
        try{
            p->lease.validateFiles(true);
            snapshotParent(options.destinationDirectory);
            auto relative=options.destinationDirectory.lexically_relative(p->options.path.parent_path());
            need(relative.empty()||relative.is_absolute()||*relative.begin()=="..","Snapshot stage must be outside the live profile directory");
            if(options.publication){
                for(const auto& protectedDirectory:{p->options.path.parent_path(),options.destinationDirectory}){
                    const auto targetRelative=options.publication->destination.lexically_relative(protectedDirectory);
                    need(!targetRelative.empty()&&!targetRelative.is_absolute()&&*targetRelative.begin()=="..",
                        "Backup publication target must be outside the live profile and private stage","PUBLICATION_PATH");
                }
                publicationOutsideProfile(options.publication->destination,p->options.path,options.destinationDirectory);
                publicationOutsideProfile(options.destinationDirectory,p->options.path,options.destinationDirectory,false);
            }
            if(options.restorePreparation){
                publicationOutsideProfile(options.destinationDirectory,p->options.path,options.destinationDirectory,false);
                publicationOutsideProfile(options.restorePreparation->archive,p->options.path,options.destinationDirectory);
            }
            need(sqlite3_get_autocommit(p->db.handle)!=0,"Snapshot requires an idle transaction boundary","QUIESCENCE_REQUIRED");
            p->db.script("BEGIN");
            p->hook("backup_before_source_validation",op);
            inspect(p->db);
            if(!p->db.query("SELECT owner FROM pending LIMIT 1").empty()||
               !p->db.query("SELECT owner FROM checkpoint LIMIT 1").empty()||
               !p->db.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE f.owner IS NULL LIMIT 1").empty())
                throw Failure(Status::Busy,"RECOVERY_REQUIRED","Resolve original pending/checkpoint/unfinalized outcomes before backup; nothing discarded");
            auto pages=scalar(p->db,"PRAGMA page_count"),pageSize=scalar(p->db,"PRAGMA page_size");
            constexpr std::uint64_t capacity=16ULL*1024*1024*1024;
            need(pages>0&&pageSize>0&&static_cast<std::uint64_t>(pages)<=capacity/static_cast<std::uint64_t>(pageSize),"Logical profile exceeds accepted snapshot capacity","SNAPSHOT_CAPACITY");
            const auto logicalBytes=static_cast<std::uint64_t>(pages)*static_cast<std::uint64_t>(pageSize);
            const auto required=3*logicalBytes+64ULL*1024*1024;
            need(std::filesystem::space(options.destinationDirectory.parent_path()).available>=required,"Insufficient snapshot staging space; source retained","SNAPSHOT_CAPACITY");
            auto authority=streamedAuthority(p->db,check);
            auto profile=p->profile();
            auto committed=marker(p->db);
            auto journal=txt(p->db.query("PRAGMA journal_mode")[0][0]);
            p->hook("backup_boundary_captured",op);
            check();
            need(mkdir(options.destinationDirectory.c_str(),0700)==0,"Cannot create new snapshot directory","SNAPSHOT_DESTINATION_EXISTS");
            if(options.restorePreparation){
                restoreStageCreated=true;
                need(lstat(options.destinationDirectory.c_str(),&restoreStageIdentity)==0&&
                     S_ISDIR(restoreStageIdentity.st_mode),"Cannot bind newly created restore stage","RESTORE_CHANGED");
            }
            const auto destination=options.destinationDirectory/"profile.sqlite";
            ProfileLease targetLease(destination,false);
            SnapshotFD reserved(::open(destination.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));
            need(reserved.value>=0,"Cannot exclusively create snapshot file","SNAPSHOT_WRITE_FAILED");
            Database candidate;
            candidate.open(destination.string(),SQLITE_OPEN_READWRITE);
            SnapshotProgress targetProgress(candidate,check);
            candidate.script("PRAGMA synchronous=FULL;PRAGMA fullfsync=ON;PRAGMA foreign_keys=ON;");
            std::int64_t steps=0;
            {
                SnapshotCopy copy;
                copy.handle=sqlite3_backup_init(candidate.handle,"main",p->db.handle,"main");
                need(copy.handle!=nullptr,"Cannot initialize native SQLite backup","SNAPSHOT_COPY_FAILED");
                int retries=0;
                for(;;){
                    check();
                    const int code=sqlite3_backup_step(copy.handle,256);
                    ++steps;
                    p->hook("backup_step",op);
                    check();
                    if(code==SQLITE_DONE)break;
                    if(code==SQLITE_OK){retries=0;continue;}
                    if((code==SQLITE_BUSY||code==SQLITE_LOCKED)&&retries<2){
                        std::this_thread::sleep_for(std::chrono::milliseconds(retries++==0?50:150));
                        continue;
                    }
                    throw Failure(Status::DefiniteFailure,"SNAPSHOT_COPY_FAILED",sqlite3_errstr(code));
                }
                const int code=sqlite3_backup_finish(copy.handle);
                copy.handle=nullptr;
                need(code==SQLITE_OK,"Native SQLite snapshot did not finish","SNAPSHOT_COPY_FAILED");
            }
            p->hook("backup_after_copy",op);
            candidate.script("PRAGMA journal_mode=DELETE;");
            need(txt(candidate.query("PRAGMA journal_mode")[0][0])=="delete","Snapshot must be standalone DELETE mode");
            inspect(candidate);
            need(streamedAuthority(candidate,check)==authority,"Candidate differs from committed snapshot boundary","SNAPSHOT_MISMATCH");
            candidate.setProgress({});
            candidate.close();
            need(fsync(reserved.value)==0,"Snapshot sync failed","SNAPSHOT_WRITE_FAILED");
            targetLease.validateFiles(true);
            for(const char* suffix:{"-wal","-shm","-journal"}){
                struct stat st{};
                need(lstat((destination.string()+suffix).c_str(),&st)!=0&&errno==ENOENT,"Snapshot still requires transaction sidecars","SNAPSHOT_NOT_STANDALONE");
            }
            const auto validatedIdentity=pinnedSnapshotStat(reserved.value,destination);
            candidate.open(readonlyUri(destination,true),SQLITE_OPEN_READONLY|SQLITE_OPEN_URI);
            candidate.setProgress(check);
            inspect(candidate);
            need(streamedAuthority(candidate,check)==authority,"Closed standalone snapshot did not reopen at the same boundary","SNAPSHOT_MISMATCH");
            std::optional<ArchiveManifestBuilder> archiveProjection;
            if(options.includeArchiveManifest)
                archiveProjection.emplace(makeArchiveProjection(candidate,profile,committed,authority));
            candidate.setProgress({});
            candidate.close();
            need(sameSnapshotStat(validatedIdentity,pinnedSnapshotStat(reserved.value,destination)),
                 "Snapshot changed during standalone validation","SNAPSHOT_CHANGED");
            p->hook("backup_before_file_hash",op);
            auto identity=closedSnapshotIdentity(reserved.value,destination,validatedIdentity,check);
            std::unique_ptr<SnapshotFD> manifestFile;
            std::optional<struct stat> manifestStat;
            std::optional<Value> manifestReceipt;
            const auto manifestPath=options.destinationDirectory/"manifest.json";
            if(archiveProjection){
                auto metadata=archiveProjection->manifest(integer(field(identity,"bytes")),string(identity,"sha256"));
                const auto bytes=canonical(metadata);
                p->hook("backup_manifest_before_write",op);
                check();
                manifestFile=std::make_unique<SnapshotFD>(::open(manifestPath.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));
                need(manifestFile->value>=0,"Cannot exclusively create new archive manifest","ARCHIVE_MANIFEST_WRITE_FAILED");
                std::size_t written=0;
                while(written<bytes.size()){
                    check();auto count=::write(manifestFile->value,bytes.data()+written,bytes.size()-written);
                    if(count<0&&errno==EINTR)continue;
                    need(count>0,"Cannot write complete archive manifest","ARCHIVE_MANIFEST_WRITE_FAILED");
                    written+=static_cast<std::size_t>(count);
                }
                need(fsync(manifestFile->value)==0,"Cannot sync archive manifest stage","ARCHIVE_MANIFEST_WRITE_FAILED");
                p->hook("backup_manifest_written",op);
                manifestStat=pinnedSnapshotStat(manifestFile->value,manifestPath);
                auto saved=closedSnapshotIdentity(manifestFile->value,manifestPath,*manifestStat,check);
                need(integer(field(saved,"bytes"))==static_cast<std::int64_t>(bytes.size())&&string(saved,"sha256")==content::sha256(bytes),
                     "Manifest bytes changed after generation","ARCHIVE_MANIFEST_MISMATCH");
                manifestReceipt=Object{{"path",manifestPath.string()},{"file",saved},{"metadata",metadata},{"staged",true}};
                p->hook("backup_manifest_verified",op);
            }
            std::unique_ptr<SnapshotFD> archiveFile;
            std::optional<struct stat> archiveStat;
            std::optional<Value> archiveReceipt;
            const auto archivePath=options.destinationDirectory/"candidate.zip";
            if(options.includeArchiveContainer){
                need(manifestFile&&manifestReceipt,"Archive manifest unavailable","ARCHIVE_MANIFEST_REQUIRED");
                p->hook("backup_archive_before_create",op);check();
                need(sameSnapshotStat(validatedIdentity,pinnedSnapshotStat(reserved.value,destination))&&
                     sameSnapshotStat(*manifestStat,pinnedSnapshotStat(manifestFile->value,manifestPath)),
                     "Archive source changed after verification","SNAPSHOT_CHANGED");
                archiveFile=std::make_unique<SnapshotFD>(::open(archivePath.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));
                need(archiveFile->value>=0,"Cannot exclusively create archive candidate","ARCHIVE_CONTAINER_OUTPUT_EXISTS");
                const auto& manifestIdentity=field(*manifestReceipt,"file");
                auto container=writeStoredZip64(archiveFile->value,
                    {{{manifestFile->value,static_cast<std::uint64_t>(integer(field(manifestIdentity,"bytes"))),string(manifestIdentity,"sha256")},
                      {reserved.value,static_cast<std::uint64_t>(integer(field(identity,"bytes"))),string(identity,"sha256")}}},
                    check,[&](const std::string& phase){p->hook(phase,op);});
                need(sameSnapshotStat(container.verifiedIdentity,pinnedSnapshotStat(archiveFile->value,archivePath)),
                     "Archive changed after verified readback","SNAPSHOT_CHANGED");
                archiveStat=container.verifiedIdentity;
                archiveReceipt=Object{{"path",archivePath.string()},{"file",container.file},{"staged",true},{"published",false}};
                p->hook("backup_archive_verified",op);
            }
            // Cleanup SQL must remain possible after cancellation or a deadline.
            p->db.setProgress({});
            p->db.script("ROLLBACK");
            p->db.setProgress(check);
            need(streamedAuthority(p->db,check)==authority&&txt(p->db.query("PRAGMA journal_mode")[0][0])==journal,
                 "Live profile changed during snapshot","SOURCE_CHANGED");
            p->lease.validateFiles(true);
            p->hook("backup_snapshot_verified",op);
            need(sameSnapshotStat(validatedIdentity,pinnedSnapshotStat(reserved.value,destination)),
                 "Snapshot changed before receipt","SNAPSHOT_CHANGED");
            if(manifestFile)need(sameSnapshotStat(*manifestStat,pinnedSnapshotStat(manifestFile->value,manifestPath)),
                                 "Manifest changed before receipt","SNAPSHOT_CHANGED");
            if(archiveFile)need(sameSnapshotStat(*archiveStat,pinnedSnapshotStat(archiveFile->value,archivePath)),
                                "Archive changed before receipt","SNAPSHOT_CHANGED");
            check();
            auto elapsed=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count();
            Object receipt{{"format","Fathom.BackupSnapshotStage"},{"stage_version",num(1)},
                {"profile_id",profile},{"data_schema",num(schemaVersion(p->db))},{"schema_sha256",schemaHash(p->db)},
                {"committed_seq",num(committed)},{"authority",authority},{"file",identity},
                {"destination",destination.string()},{"logical_source_bytes",num(static_cast<std::int64_t>(logicalBytes))},
                {"required_free_bytes",num(static_cast<std::int64_t>(required))},{"backup_steps",num(steps)},
                {"step_pages",num(256)},{"elapsed_ms",num(elapsed)},{"sqlite_version",sqlite3_libversion()},
                {"standalone",true},{"stage_complete",true},{"archive_published",false},{"restore_performed",false},
                {"caller_stopped_attestation",true},{"required_resume_state","stopped"},
                {"content_compatibility","Original references preserved; current availability/admission not assessed"}};
            if(manifestReceipt)receipt.emplace("manifest",*manifestReceipt);
            if(archiveReceipt)receipt.emplace("archive",*archiveReceipt);
            if(options.publication){
                auto publicationCheck=[&]{
                    if(options.cancelled&&options.cancelled())throw EnvelopeError("ARCHIVE_CANCELLED","Backup publication cancelled; inspect its original operation and retained files");
                    if(std::chrono::steady_clock::now()>=end)throw EnvelopeError("ARCHIVE_DEADLINE","Backup publication deadline reached; inspect its original operation and retained files");
                    try{
                        p->lease.validateFiles(true);
                        publicationOutsideProfile(options.publication->destination,p->options.path,options.destinationDirectory);
                        if(!sameSnapshotStat(validatedIdentity,pinnedSnapshotStat(reserved.value,destination))||
                           !sameSnapshotStat(*manifestStat,pinnedSnapshotStat(manifestFile->value,manifestPath)))
                            throw EnvelopeError("ARCHIVE_CHANGED","Held backup database or manifest changed during publication");
                    }catch(const Failure& e){throw EnvelopeError("ARCHIVE_CHANGED",std::string("Held backup source unavailable during publication: ")+e.what());}
                };
                BackupPublisher publisher(op,*options.publication,options.destinationDirectory,publicationCheck,
                    [&](const std::string& phase){p->hook(phase,op);});
                const auto& mf=field(*manifestReceipt,"file");
                Value original=Object{{"profile_id",profile},{"committed_seq",num(committed)},
                    {"authority_sha256",field(authority,"sha256")},{"schema_sha256",schemaHash(p->db)},
                    {"profile_sha256",field(identity,"sha256")},{"profile_bytes",field(identity,"bytes")},
                    {"manifest_sha256",field(mf,"sha256")},{"manifest_bytes",field(mf,"bytes")}};
                auto published=publisher.publish(archiveFile->value,field(*archiveReceipt,"file"),original);
                const auto state=published.state==BackupPublicationState::Published?Status::Confirmed:
                    published.state==BackupPublicationState::Unresolved?Status::Unresolved:Status::DefiniteFailure;
                receipt.at("archive_published")=field(published.evidence,"archive_published");
                auto& ar=receipt.at("archive").object();ar.at("published")=field(published.evidence,"archive_published");
                ar.at("staged")=published.state==BackupPublicationState::Unresolved?Value(nullptr):Value(published.state==BackupPublicationState::NotPublished);
                ar.at("path")=published.state==BackupPublicationState::Published?Value(options.publication->destination.string()):
                    published.state==BackupPublicationState::NotPublished?Value(archivePath.string()):Value(nullptr);
                ar.emplace("original_stage_path",archivePath.string());
                receipt.emplace("publication",published.evidence);
                receipt.at("elapsed_ms")=num(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count());
                return Reply{state,op,profile,published.code,published.message,std::move(receipt)};
            }
            if(options.restorePreparation){
                auto retained=[&]{
                    check();p->lease.validateFiles(true);
                    need(sameSnapshotStat(validatedIdentity,pinnedSnapshotStat(reserved.value,destination))&&
                         sameSnapshotStat(*manifestStat,pinnedSnapshotStat(manifestFile->value,manifestPath))&&
                         sameSnapshotStat(*archiveStat,pinnedSnapshotStat(archiveFile->value,archivePath)),
                         "Original restore backup changed","RESTORE_CHANGED");
                };
                auto finalAuthority=[&]{
                    need(streamedAuthority(p->db,check)==authority,"Live authority changed during restore preparation","SOURCE_CHANGED");
                };
                auto prepared=detail::prepareRestore(op,*options.restorePreparation,p->options.path,receipt,end,retained,finalAuthority,
                    [&](const std::string& phase){p->hook(phase,op);});
                retained();receipt.emplace("restore_preparation",std::move(prepared));
                receipt.at("elapsed_ms")=num(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count());
                return Reply{Status::Confirmed,op,profile,"RESTORE_PREPARED","Preview ready; explicit confirmation and separate apply required. Live profile unchanged.",std::move(receipt)};
            }
            return p->okay(op,profile,std::move(receipt));
        }catch(...){
            auto original=std::current_exception();
            p->db.setProgress({});
            if(sqlite3_get_autocommit(p->db.handle)==0){
                try{p->db.script("ROLLBACK");}
                catch(...){p->quarantined=true;throw Failure(Status::Unresolved,"SNAPSHOT_CLEANUP_UNCERTAIN","Snapshot read-transaction cleanup uncertain; close and inspect/reconcile original profile before more work");}
            }
            if(restoreStageCreated&&!p->quarantined){
                struct stat current{};
                if(lstat(options.destinationDirectory.c_str(),&current)==0&&
                   S_ISDIR(current.st_mode)&&current.st_dev==restoreStageIdentity.st_dev&&
                   current.st_ino==restoreStageIdentity.st_ino&&current.st_uid==getuid()&&
                   (current.st_mode&077)==0){
                    std::error_code ignored;
                    std::filesystem::remove_all(options.destinationDirectory,ignored);
                }
            }
            std::rethrow_exception(original);
        }
    },false,true);
}
ProfileStore::Future ProfileStore::reconcileBackupPublication(std::string op,BackupSnapshotOptions options){
    auto* p=impl_.get();const auto started=std::chrono::steady_clock::now();
    return p->submit(op,"",[=]{
        Value unavailable=Object{{"operation",op},{"stage",options.destinationDirectory.string()},
            {"destination",options.publication?Value(options.publication->destination.string()):Value(nullptr)},
            {"archive_published",nullptr},{"restore_performed",false},{"required_resume_state","stopped"}};
        try{
        if(!options.stopped||options.unresolvedWrites)throw Failure(Status::Busy,"QUIESCENCE_REQUIRED","Stop practice and reconcile outstanding writes before publication reconciliation");
        need(options.publication.has_value(),"Original publication request required","PUBLICATION_REQUIRED");
        need(options.timeout.count()>0&&options.timeout<=std::chrono::seconds(300),"Reconciliation timeout must be positive and at most300seconds");
        p->lease.validateFiles(true);
        need(sqlite3_get_autocommit(p->db.handle)!=0,"Reconciliation requires idle writer","QUIESCENCE_REQUIRED");
        if(!p->db.query("SELECT owner FROM pending LIMIT 1").empty()||!p->db.query("SELECT owner FROM checkpoint LIMIT 1").empty()||
           !p->db.query("SELECT i.owner FROM identity i LEFT JOIN finalized f ON f.owner=i.owner WHERE f.owner IS NULL LIMIT 1").empty())
            throw Failure(Status::Busy,"RECOVERY_REQUIRED","Resolve original profile outcomes before backup reconciliation");
        auto check=[&]{
            if(options.cancelled&&options.cancelled())throw EnvelopeError("ARCHIVE_CANCELLED","Original backup reconciliation cancelled; retained files require inspection");
            if(std::chrono::steady_clock::now()-started>=options.timeout)throw EnvelopeError("ARCHIVE_DEADLINE","Original backup reconciliation deadline reached; retained files require inspection");
            p->lease.validateFiles(true);
        };
        BackupPublisher publisher(op,*options.publication,options.destinationDirectory,check,
            [&](const std::string& phase){p->hook(phase,op);});
        auto result=publisher.reconcile(p->profile(),schemaHash(p->db));
        auto status=result.state==BackupPublicationState::Published?Status::Confirmed:
            result.state==BackupPublicationState::NotPublished?Status::DefinitelyAbsent:Status::Unresolved;
        return Reply{status,op,p->profile(),result.code,result.message,std::move(result.evidence)};
        }catch(const EnvelopeError& e){return Reply{Status::Unresolved,op,"",e.code,e.what(),unavailable};}
        catch(const Failure& e){return Reply{Status::Unresolved,op,"",e.code,e.what(),unavailable};}
        catch(const std::exception& e){return Reply{Status::Unresolved,op,"","PUBLICATION_RECONCILE_UNAVAILABLE",e.what(),unavailable};}
    },false,true);
}
ProfileStore::Future ProfileStore::snapshot(std::string op){auto* p=impl_.get();return p->submit(op,"",[=]{if(p->quarantined)throw Failure(Status::Unresolved,"STORE_UNCERTAIN","Reopen before reading authoritative snapshot");inspect(p->db);auto full=state(p->db,true);return p->okay(op,p->profile(),Object{{"profile_id",p->profile()},{"committed_seq",num(marker(p->db))},{"authoritative",full},{"snapshot_sha256",content::sha256(canonical(full))},{"evidence_sha256",stateHash(p->db,false)},{"content_compatibility","Not assessed; preserve unavailable historical references"},{"schema_sha256",schemaHash(p->db)},{"connection_policy",Object{{"sqlite_version",sqlite3_libversion()},{"journal_mode",txt(p->db.query("PRAGMA journal_mode")[0][0])},{"synchronous",num(scalar(p->db,"PRAGMA synchronous"))},{"fullfsync",num(scalar(p->db,"PRAGMA fullfsync"))},{"checkpoint_fullfsync",num(scalar(p->db,"PRAGMA checkpoint_fullfsync"))},{"foreign_keys",num(scalar(p->db,"PRAGMA foreign_keys"))},{"busy_timeout",num(scalar(p->db,"PRAGMA busy_timeout"))},{"wal_autocheckpoint",num(scalar(p->db,"PRAGMA wal_autocheckpoint"))},{"journal_size_limit",num(scalar(p->db,"PRAGMA journal_size_limit"))},{"cache_size",num(scalar(p->db,"PRAGMA cache_size"))}}}});});}
} // namespace fathom::storage
