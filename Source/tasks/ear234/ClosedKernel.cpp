#include "ClosedKernel.hpp"
#include "UnicodeCasefold.hpp"
#include "GeneratedEar234.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
#include <algorithm>
#include <atomic>
#include <limits>
#include <iomanip>
#include <functional>
#include <numeric>
#include <regex>
#include <set>
#include <sstream>

namespace fathom::tasks::ear234::closed {
namespace {
[[noreturn]] void refuse(const std::string& s) { throw std::runtime_error("closed234:"+s); }
const json::Value& field(const json::Value& j,const std::string& k) { auto p=j.find(k); if(!p)refuse("missing instruction field:"+k);return *p; }
std::string tag(const json::Value& j) { return field(j,"_").string(); }
std::string name(const json::Value& j,const std::string& k) {return field(j,k).string();}
Value make(std::string k) { auto p=std::make_shared<Node>();p->kind=std::move(k);return Value(p); }
Value functionValue(const json::Value& code,Value bound=Value::none()) { auto v=make("function");v.p->code=code;if(bound.kind()!="none")v.p->bound=bound.p;return v; }
Value builtin(std::string s,Value bound=Value::none()) {auto v=make("builtin");v.p->text=std::move(s);if(bound.kind()!="none")v.p->bound=bound.p;return v;}
std::int64_t exact(__int128 n) {if(n<std::numeric_limits<std::int64_t>::min()||n>std::numeric_limits<std::int64_t>::max())refuse("integer arithmetic limit");return static_cast<std::int64_t>(n);}
bool numeric(const Value& v) {return v.kind()=="integer"||v.kind()=="boolean"||v.kind()=="fraction"||v.kind()=="float";}
Value fraction(std::int64_t n,std::int64_t d) {if(!d)refuse("zero rational denominator");if(d<0){n=exact(-(__int128)n);d=exact(-(__int128)d);}auto g=std::gcd(n,d);auto v=make("fraction");v.p->number=n/g;v.p->denominator=d/g;return v;}
std::pair<std::int64_t,std::int64_t> quantity(const Value& v) {if(v.kind()=="unknown")throw NeedInput{};if(!numeric(v))refuse("number required");return {v.p->number,v.kind()=="fraction"||v.kind()=="float"?v.p->denominator:1};}
bool less(const Value& a,const Value& b) {if(a.kind()=="unknown"||b.kind()=="unknown")throw NeedInput{};if(numeric(a)&&numeric(b)){auto x=quantity(a),y=quantity(b);return (__int128)x.first*y.second<(__int128)y.first*x.second;}if(a.kind()=="string"&&b.kind()=="string")return a.text()<b.text();if(a.kind()==b.kind()&&(a.kind()=="tuple"||a.kind()=="list"))return std::lexicographical_compare(a.p->values.begin(),a.p->values.end(),b.p->values.begin(),b.p->values.end(),less);refuse("closed ordering");}
std::size_t length(const Value& v) {if(v.kind()=="unknown")throw NeedInput{};if(v.kind()=="dict")return v.p->entries.size();if(v.kind()=="string")return manual_procedure_graph_support::utf8TextLength(v.text());if(v.kind()=="list"||v.kind()=="tuple"||v.kind()=="set")return v.p->values.size();refuse("length type");}
Value binary(const std::string& op,const Value& a,const Value& b) {
    if(a.kind()=="unknown"||b.kind()=="unknown")throw NeedInput{};
    if(op=="Add"&&a.kind()=="string"&&b.kind()=="string")return Value::string(a.text()+b.text());
    if(op=="Add"&&a.kind()==b.kind()&&(a.kind()=="tuple"||a.kind()=="list")){auto z=a.items();auto v=b.items();z.insert(z.end(),v.begin(),v.end());return Value::sequence(a.kind(),z);}
    if(op=="Mult"&&((a.kind()=="tuple"||a.kind()=="list"||a.kind()=="string")&&b.kind()=="integer")){if(b.number()<0||b.number()>4096)refuse("sequence repeat limit");if(a.kind()=="string"){std::string s;for(int i=0;i<b.number();++i)s+=a.text();return Value::string(s);}std::vector<Value> z;for(int i=0;i<b.number();++i){auto x=a.items();z.insert(z.end(),x.begin(),x.end());}return Value::sequence(a.kind(),z);}
    auto x=quantity(a),y=quantity(b);
    if(op=="Add"||op=="Sub"){auto n=exact((__int128)x.first*y.second+(op=="Add"?1:-1)*(__int128)y.first*x.second),d=exact((__int128)x.second*y.second);return a.kind()=="fraction"||b.kind()=="fraction"?fraction(n,d):Value::integer(n);}
    if(op=="Mult"){auto n=exact((__int128)x.first*y.first),d=exact((__int128)x.second*y.second);return a.kind()=="fraction"||b.kind()=="fraction"?fraction(n,d):Value::integer(n);}
    if(op=="Mod"&&x.second==1&&y.second==1){if(!y.first)refuse("mod zero");auto n=x.first%y.first;if(n&&(n<0)!=(y.first<0))n+=y.first;return Value::integer(n);}
    refuse("unadmitted binary operator:"+op);
}
bool space(const std::string& s) {std::uint32_t c=0;for(unsigned char b:s)c=c?((c<<6)|(b&0x3f)):b<0x80?b:b<0xe0?(b&0x1f):b<0xf0?(b&0x0f):(b&7);return (c>=9&&c<=13)||(c>=28&&c<=32)||c==0x85||c==0xa0||c==0x1680||(c>=0x2000&&c<=0x200a)||c==0x2028||c==0x2029||c==0x202f||c==0x205f||c==0x3000;}
std::string trim(const std::string& s) {manual_procedure_graph_support::utf8TextLength(s);std::size_t first=s.size(),last=0;for(std::size_t i=0;i<s.size();){auto begin=i++;while(i<s.size()&&(static_cast<unsigned char>(s[i])&0xc0)==0x80)++i;if(!space(s.substr(begin,i-begin))){first=std::min(first,begin);last=i;}}return first==s.size()?"":s.substr(first,last-first);}
Value copied(const Value& v,std::map<const Node*,Value>& seen) {if(!v.p)return Value::none();auto i=seen.find(v.p.get());if(i!=seen.end())return i->second;auto z=make(v.kind());seen[v.p.get()]=z;z.p->text=v.p->text;z.p->number=v.p->number;z.p->denominator=v.p->denominator;z.p->code=v.p->code;z.p->closure=v.p->closure;z.p->bound=v.p->bound;for(auto& x:v.p->values)z.p->values.push_back(copied(x,seen));for(auto& x:v.p->entries)z.p->entries.emplace_back(copied(x.first,seen),copied(x.second,seen));for(auto& x:v.p->attributes)z.p->attributes[x.first]=copied(x.second,seen);return z;}
std::atomic<std::uint64_t> serial{1};
}
Value::Value():p(std::make_shared<Node>()){}
Value::Value(std::shared_ptr<Node> v):p(std::move(v)){}
Value Value::none(){return make("none");}
Value Value::boolean(bool x){auto v=make("boolean");v.p->number=x;return v;}
Value Value::integer(std::int64_t x){auto v=make("integer");v.p->number=x;return v;}
Value Value::string(std::string x){auto v=make("string");v.p->text=std::move(x);return v;}
Value Value::sequence(std::string k,const std::vector<Value>& xs){auto v=make(k);for(auto& x:xs)if(k!="set"||!v.has(x))v.p->values.push_back(x);return v;}
Value Value::dictionary(){return make("dict");}
Value Value::object(std::string c){auto v=make("object");v.p->text=std::move(c);return v;}
Value Value::unknown(){return make("unknown");}
std::string Value::kind()const{return p->kind;}
std::string Value::text()const{if(kind()=="unknown")throw NeedInput{};if(kind()!="string")refuse("string required");return p->text;}
std::int64_t Value::number()const{if(kind()=="unknown")throw NeedInput{};if(kind()!="integer"&&kind()!="boolean")refuse("integer required");return p->number;}
bool Value::truth()const {if(kind()=="unknown")throw NeedInput{};if(kind()=="none")return false;if(numeric(*this))return p->number!=0;if(kind()=="string")return !p->text.empty();if(kind()=="dict")return !p->entries.empty();if(kind()=="list"||kind()=="tuple"||kind()=="set")return !p->values.empty();return true;}
std::vector<Value> Value::items()const {if(kind()=="unknown")throw NeedInput{};if(kind()=="dict"){std::vector<Value> z;for(auto& x:p->entries)z.push_back(x.first);return z;}if(kind()=="string"){std::vector<Value> z;length(*this);for(std::size_t i=0;i<p->text.size();){auto begin=i++;while(i<p->text.size()&&(static_cast<unsigned char>(p->text[i])&0xc0)==0x80)++i;z.push_back(string(p->text.substr(begin,i-begin)));}return z;}if(kind()=="list"||kind()=="tuple"||kind()=="set")return p->values;refuse("iteration type");}
bool Value::has(const Value& x)const {if(kind()=="unknown"||x.kind()=="unknown")throw NeedInput{};if(kind()=="string")return p->text.find(x.text())!=std::string::npos;for(auto& v:items())if(v==x)return true;return false;}
Value Value::get(const Value& k)const {if(kind()=="unknown"||k.kind()=="unknown")throw NeedInput{};if(kind()=="dict"){for(auto& x:p->entries)if(x.first==k)return x.second;refuse("missing dictionary key");}if(kind()=="list"||kind()=="tuple"||kind()=="string"){auto i=k.number();auto xs=items();if(i<0)i+=static_cast<std::int64_t>(xs.size());if(i<0||static_cast<std::size_t>(i)>=xs.size())refuse("source index range");return xs[i];}refuse("subscript type");}
Value Value::get(const std::string& k)const{return get(string(k));}
Value Value::getOr(const std::string& k,Value d)const {return has(string(k))?get(k):d;}
void Value::put(Value k,Value v) {if(kind()=="unknown")throw NeedInput{};if(kind()=="dict"){for(auto& x:p->entries)if(x.first==k){x.second=v;return;}p->entries.emplace_back(k,v);return;}if(kind()=="list"){auto i=k.number();if(i<0)i+=static_cast<std::int64_t>(p->values.size());if(i<0||static_cast<std::size_t>(i)>=p->values.size())refuse("list write range");p->values[i]=v;return;}refuse("write type");}
void Value::attribute(std::string k,Value v){if(kind()!="object")refuse("attribute write type");p->attributes[k]=v;}
Value Value::attribute(const std::string& k)const {if(kind()=="unknown")throw NeedInput{};auto i=p->attributes.find(k);if(i==p->attributes.end())refuse("missing attribute:"+k);return i->second;}
bool Value::operator==(const Value& b)const {if(kind()=="unknown"||b.kind()=="unknown")throw NeedInput{};if(numeric(*this)&&numeric(b)){auto x=quantity(*this),y=quantity(b);return (__int128)x.first*y.second==(__int128)y.first*x.second;}if(kind()!=b.kind())return false;if(kind()=="none")return true;if(kind()=="string"||kind()=="type"||kind()=="builtin"||kind()=="class")return p->text==b.p->text;if(kind()=="dict"){if(p->entries.size()!=b.p->entries.size())return false;for(auto& e:p->entries)if(!b.has(e.first)||b.get(e.first)!=e.second)return false;return true;}if(kind()=="set"){if(p->values.size()!=b.p->values.size())return false;for(auto& e:p->values)if(!b.has(e))return false;return true;}if(kind()=="list"||kind()=="tuple")return p->values==b.p->values;return p==b.p;}
Value fromJson(const json::Value& j){if(j.null())return Value::none();if(j.isBool())return Value::boolean(j.boolean());if(j.isNumber()){std::int64_t n;if(j.integer(n))return Value::integer(n);auto s=std::get<json::Number>(j.data).token;auto dot=s.find('.');if(dot==std::string::npos||s.find_first_of("eE")!=std::string::npos||s.size()>18)refuse("unadmitted decimal literal");auto plain=s;plain.erase(dot,1);std::int64_t denominator=1;for(std::size_t i=dot+1;i<s.size();++i)denominator=exact((__int128)denominator*10);auto v=make("float");v.p->number=std::stoll(plain);v.p->denominator=denominator;v.p->text=s;return v;}if(j.isString())return Value::string(j.string());if(j.isArray()){std::vector<Value> z;for(auto& x:j.array())z.push_back(fromJson(x));return Value::sequence("list",z);}auto z=Value::dictionary();for(auto& x:j.object())z.put(Value::string(x.first),fromJson(x.second));return z;}
json::Value toJson(const Value& v){if(v.kind()=="none")return nullptr;if(v.kind()=="boolean")return bool(v.p->number);if(v.kind()=="integer")return json::Value::fromInteger(v.p->number);if(v.kind()=="float")return json::Number{v.p->text};if(v.kind()=="string")return v.p->text;if(v.kind()=="list"||v.kind()=="tuple"||v.kind()=="set"){json::Value::Array z;for(auto& x:v.items())z.push_back(toJson(x));return z;}if(v.kind()=="dict"){json::Value::Object z;for(auto& x:v.p->entries){std::string k=x.first.kind()=="string"?x.first.text():std::to_string(x.first.number());z[k]=toJson(x.second);}return z;}if(v.kind()=="fraction")return json::Value::Array{json::Value::fromInteger(v.p->number),json::Value::fromInteger(v.p->denominator)};refuse("nondata value export");}
Value clone(const Value& v){std::map<const Node*,Value> seen;return copied(v,seen);}
std::string unicodeStrip(const std::string& s){return trim(s);}
json::Value Kernel::continuationState(const Value& root) const {
    // Tagged data preserves key types, container kind, mutable aliasing and cycles.
    // Only this kernel's fresh local scope is normalized for legal replay.
    std::map<const Node*, std::int64_t> seen;
    std::size_t count=0;
    std::function<json::Value(const Value&,std::size_t)> visit;
    visit=[&](const Value& v,std::size_t depth)->json::Value {
        if(!v.p||depth>96||++count>2000000)refuse("private state size/depth");
        const auto& n=*v.p;const auto& k=n.kind;
        static const std::set<std::string> data{"none","boolean","integer","float","string","list","tuple","set","dict","fraction","object","unknown"};
        if(!data.count(k)||n.closure||n.bound||n.unused||!n.code.null())refuse("private state contains executable/foreign capability");
        const bool compound=k=="list"||k=="tuple"||k=="set"||k=="dict"||k=="object";
        json::Value::Object out{{"kind",k}};
        if(compound){auto old=seen.find(v.p.get());if(old!=seen.end())return json::Value::Object{{"ref",json::Value::fromInteger(old->second)}};auto id=static_cast<std::int64_t>(seen.size());seen.emplace(v.p.get(),id);out["id"]=json::Value::fromInteger(id);}
        out["text"]=n.text==instance_?json::Value(json::Value::Object{{"fresh_kernel_scope",true}}):json::Value(n.text);
        out["number"]=json::Value::fromInteger(n.number);out["denominator"]=json::Value::fromInteger(n.denominator);
        json::Value::Array values,entries;json::Value::Object attrs;
        for(const auto& x:n.values)values.push_back(visit(x,depth+1));
        for(const auto& x:n.entries){auto key=visit(x.first,depth+1);auto value=visit(x.second,depth+1);entries.emplace_back(json::Value::Array{std::move(key),std::move(value)});}
        for(const auto& x:n.attributes)attrs.emplace(x.first,visit(x.second,depth+1));
        out["values"]=std::move(values);out["entries"]=std::move(entries);out["attributes"]=std::move(attrs);return out;
    };
    return visit(root,0);
}
void Kernel::consume(){if(!fuel_--)refuse("instruction fuel limit");}
Kernel::Kernel(const json::Value& code){instance_="closed234-"+std::to_string(serial++);Environment e;statements(field(code,"body").array(),e);globals_=std::move(e);}
Kernel Kernel::fromPinnedSha(const std::string& exactSha){static const auto table=json::parse(generatedTable);auto module=field(table,"kernels").find(exactSha);if(!module)refuse("foreign compiled kernel identity");return Kernel(*module);}
Value Kernel::construct(const std::string& c,const std::vector<Value>& a){fuel_=250000;auto i=globals_.find(c);if(i==globals_.end()||i->second.kind()!="class")refuse("unadmitted constructor");return call(i->second,a);}
bool Kernel::hasMethod(const Value& self,const std::string& n)const {auto c=classes_.find(self.p->text);if(c==classes_.end())return false;for(auto& j:field(c->second,"body").array())if(tag(j)=="FunctionDef"&&name(j,"name")==n)return true;return false;}
Value Kernel::invoke(Value self,const std::string& n,const std::vector<Value>& a){fuel_=250000;return call(attribute(self,n),a);}
bool Kernel::enabled(const Value& self,const std::string& n,std::size_t args,bool token){
    auto s=clone(self);
    // An input validator may precede the action's state check. Enforce exact
    // literal state sets before the unknown-input probe; never infer an answer.
    if(token){auto cls=classes_.find(self.p->text);if(cls!=classes_.end())for(auto& method:field(cls->second,"body").array())if(tag(method)=="FunctionDef"&&name(method,"name")==n){for(auto& statement:field(method,"body").array()){if(tag(statement)!="Expr")continue;auto&call=field(statement,"value");if(tag(call)!="Call"||tag(field(call,"func"))!="Attribute"||name(field(call,"func"),"attr")!="check")continue;auto&ca=field(call,"args").array();if(ca.size()<2||tag(ca[1])!="Tuple")break;bool literal=true;std::vector<Value> states;for(auto&state:field(ca[1],"elts").array()){if(tag(state)!="Constant"||!field(state,"value").isString()){literal=false;break;}states.push_back(Value::string(field(state,"value").string()));}if(literal){try{invoke(s,"check",{invoke(s,"token"),Value::sequence("tuple",states)});}catch(const std::exception&){return false;}}break;}break;}}
    std::vector<Value> a;if(token)a.push_back(invoke(s,"token"));for(std::size_t i=0;i<args;++i)a.push_back(Value::unknown());try{invoke(s,n,a);return true;}catch(const NeedInput&){return true;}catch(const std::exception&){return false;}
}
Value Kernel::attribute(Value v,const std::string& k) {
    if(v.kind()=="unknown")throw NeedInput{};
    if(v.kind()=="object"){auto i=v.p->attributes.find(k);if(i!=v.p->attributes.end())return i->second;auto c=classes_.find(v.p->text);if(c!=classes_.end()){auto g=globals_.find(v.p->text);if(g!=globals_.end()){auto q=g->second.p->attributes.find(k);if(q!=g->second.p->attributes.end())return q->second;}for(auto& j:field(c->second,"body").array())if(tag(j)=="FunctionDef"&&name(j,"name")==k){auto& params=field(field(j,"args"),"args").array();return functionValue(j,!params.empty()&&name(params[0],"arg")=="self"?v:Value::none());}}refuse("closed object attribute:"+k);}
    if(v.kind()=="class"){auto i=v.p->attributes.find(k);if(i!=v.p->attributes.end())return i->second;refuse("closed class attribute:"+k);}
    if(v.kind()=="namespace")return builtin(v.p->text+"."+k);
    if(v.kind()=="fraction"&&(k=="numerator"||k=="denominator"))return Value::integer(k=="numerator"?v.p->number:v.p->denominator);
    static const std::set<std::string> methods{"get","update","pop","items","values","append","index","add","discard","clear","strip","split","join","casefold","lower","replace"};
    if(methods.count(k))return builtin(k,v);
    refuse("unadmitted attribute:"+k);
}
Value Kernel::function(const json::Value& code,std::vector<Value> a,const std::map<std::string,Value>& kw,const std::shared_ptr<Environment>& closure) {
    // Legacy views can mutate their disclosure history just by being read.
    // They are not invoked for learner rendering or internal action returns.
    if(tag(code)=="FunctionDef"&&name(code,"name")=="learner_view"&&!explicitReference_)return Value::dictionary();
    Environment e=closure?*closure:globals_;
    const auto& args=field(field(code,"args"),"args").array();const auto& defaults=field(field(code,"args"),"defaults").array();
    if(a.size()>args.size())refuse("argument arity");
    for(std::size_t i=0;i<args.size();++i){auto n=name(args[i],"arg");if(i<a.size())e[n]=a[i];else if(kw.count(n))e[n]=kw.at(n);else if(i>=args.size()-defaults.size())e[n]=evaluate(defaults[i-(args.size()-defaults.size())],e);else refuse("missing argument:"+n);}
    for(auto& x:kw){bool found=false;for(auto& q:args)found|=name(q,"arg")==x.first;if(!found)refuse("unknown keyword");}
    try{if(tag(code)=="Lambda")return evaluate(field(code,"body"),e);statements(field(code,"body").array(),e);}catch(const Return& r){return r.value;}
    return Value::none();
}
Value Kernel::call(Value f,const std::vector<Value>& supplied,const std::map<std::string,Value>& kw) {
    consume();if(f.kind()=="unknown")throw NeedInput{};
    if(f.kind()=="function"){auto a=supplied;if(f.p->bound)a.insert(a.begin(),Value(f.p->bound));return function(f.p->code,a,kw,f.p->closure);}
    if(f.kind()=="class"){if(f.p->text=="Refusal")return Value::string(supplied.empty()?"refusal":supplied[0].text());auto o=Value::object(f.p->text);if(hasMethod(o,"__init__"))call(attribute(o,"__init__"),supplied,kw);else if(!supplied.empty())refuse("empty class constructor");return o;}
    if(f.kind()=="type"){auto n=f.p->text;if(n=="str"){if(supplied.empty())return Value::string("");auto v=supplied[0];if(v.kind()=="string")return v;if(v.kind()=="integer")return Value::string(std::to_string(v.number()));if(v.kind()=="boolean")return Value::string(v.truth()?"True":"False");refuse("closed str conversion");}if(n=="bool")return Value::boolean(!supplied.empty()&&supplied[0].truth());if(n=="int")return Value::integer(supplied.empty()?0:supplied[0].number());if(n=="dict")return supplied.empty()?Value::dictionary():clone(supplied[0]);if(n=="list"||n=="tuple"||n=="set")return Value::sequence(n,supplied.empty()?std::vector<Value>{}:supplied[0].items());refuse("type constructor:"+n);}
    if(f.kind()!="builtin")refuse("uncallable instruction");auto n=f.p->text;auto a=supplied;
    for(auto& v:a)if(v.kind()=="unknown")throw NeedInput{};
    if(f.p->bound){auto v=Value(f.p->bound);
        if(n=="get"){if(a.empty()||a.size()>2)refuse("get arity");return v.has(a[0])?v.get(a[0]):a.size()==2?a[1]:Value::none();}
        if(n=="update"){if(v.kind()!="dict")refuse("dict update");if(!a.empty()){if(a.size()!=1||a[0].kind()!="dict")refuse("update arity");for(auto& x:a[0].p->entries)v.put(x.first,x.second);}for(auto& x:kw)v.put(Value::string(x.first),x.second);return Value::none();}
        if(n=="pop"){if(a.empty()||a.size()>2||v.kind()!="dict")refuse("dict pop");for(auto i=v.p->entries.begin();i!=v.p->entries.end();++i)if(i->first==a[0]){auto z=i->second;v.p->entries.erase(i);return z;}if(a.size()==2)return a[1];refuse("pop missing");}
        if(n=="items"||n=="values"){if(!a.empty()||v.kind()!="dict")refuse("dict iterate");std::vector<Value> z;for(auto& x:v.p->entries)z.push_back(n=="values"?x.second:Value::sequence("tuple",{x.first,x.second}));return Value::sequence("list",z);}
        if(n=="append"){if(a.size()!=1||v.kind()!="list")refuse("list append");v.p->values.push_back(a[0]);return Value::none();}
        if(n=="index"){if(a.size()!=1)refuse("index arity");auto xs=v.items();for(std::size_t i=0;i<xs.size();++i)if(xs[i]==a[0])return Value::integer(i);refuse("index missing");}
        if(n=="add"||n=="discard"){if(a.size()!=1||v.kind()!="set")refuse("set operation");if(n=="add"&&!v.has(a[0]))v.p->values.push_back(a[0]);if(n=="discard")v.p->values.erase(std::remove(v.p->values.begin(),v.p->values.end(),a[0]),v.p->values.end());return Value::none();}
        if(n=="clear"){if(!a.empty())refuse("clear arity");v.p->values.clear();v.p->entries.clear();return Value::none();}
        if(n=="strip"){if(!a.empty())refuse("strip arity");return Value::string(trim(v.text()));}
        if(n=="lower"||n=="casefold"){if(!a.empty())refuse("casefold arity");auto s=v.text();manual_procedure_graph_support::utf8TextLength(s);std::string out;for(std::size_t i=0;i<s.size();){auto begin=i;unsigned c=static_cast<unsigned char>(s[i++]);if(c>=0x80){c=c<0xe0?c&31:c<0xf0?c&15:c&7;while(i<s.size()&&(static_cast<unsigned char>(s[i])&0xc0)==0x80)c=(c<<6)|(static_cast<unsigned char>(s[i++])&63);}auto it=unicodeCasefoldTable().find(c);if(n=="casefold"&&it!=unicodeCasefoldTable().end())out+=it->second;else if(n=="lower"&&c>=65&&c<=90)out+=static_cast<char>(c+32);else out+=s.substr(begin,i-begin);}return Value::string(out);}
        if(n=="split"){std::vector<Value> z;auto s=v.text();if(a.empty()){manual_procedure_graph_support::utf8TextLength(s);std::string token;for(std::size_t i=0;i<s.size();){auto begin=i++;while(i<s.size()&&(static_cast<unsigned char>(s[i])&0xc0)==0x80)++i;auto c=s.substr(begin,i-begin);if(space(c)){if(!token.empty()){z.push_back(Value::string(token));token.clear();}}else token+=c;}if(!token.empty())z.push_back(Value::string(token));}else if(a.size()==1){auto sep=a[0].text();if(sep.empty())refuse("empty separator");std::size_t pos=0,next;while((next=s.find(sep,pos))!=std::string::npos){z.push_back(Value::string(s.substr(pos,next-pos)));pos=next+sep.size();}z.push_back(Value::string(s.substr(pos)));}else refuse("split arity");return Value::sequence("list",z);}
        if(n=="join"){if(a.size()!=1)refuse("join arity");std::string s;bool first=true;for(auto& x:a[0].items()){if(!first)s+=v.text();first=false;s+=x.text();}return Value::string(s);}
        if(n=="replace"){if(a.size()!=2)refuse("replace arity");auto s=v.text(),x=a[0].text(),y=a[1].text();if(x.empty())refuse("empty replace target");std::size_t p=0;while((p=s.find(x,p))!=std::string::npos){s.replace(p,x.size(),y);p+=y.size();}return Value::string(s);}
        refuse("unadmitted bound method:"+n);
    }
    if(n=="deepcopy"||n=="copy.deepcopy"){if(a.size()!=1)refuse("copy arity");return clone(a[0]);}
    if(n=="ValueError"||n=="Refusal")return Value::string(a.empty()?"refusal":a[0].text());
    if(n=="uuid4"){auto x=Value::object("native_uuid");x.attribute("hex",Value::string(instance_));return x;}
    if(n=="len"){if(a.size()!=1)refuse("len arity");return Value::integer(length(a[0]));}
    if(n=="type"){if(a.size()!=1)refuse("type arity");auto x=make("type");auto k=a[0].kind();x.p->text=k=="integer"?"int":k=="boolean"?"bool":k=="string"?"str":k;return x;}
    if(n=="isinstance"){if(a.size()!=2)refuse("isinstance arity");auto t=a[1];auto k=a[0].kind();auto match=[&](const Value& q){return q.kind()=="type"&&(q.p->text==k||(q.p->text=="int"&&(k=="integer"||k=="boolean"))||(q.p->text=="bool"&&k=="boolean")||(q.p->text=="str"&&k=="string"));};if(t.kind()=="tuple"){for(auto& q:t.items())if(match(q))return Value::boolean(true);return Value::boolean(false);}return Value::boolean(match(t));}
    if(n=="range"){if(a.empty()||a.size()>3)refuse("range arity");auto lo=a.size()==1?0:a[0].number(),hi=a.size()==1?a[0].number():a[1].number(),step=a.size()==3?a[2].number():1;if(!step)refuse("zero range step");std::vector<Value> z;for(auto i=lo;step>0?i<hi:i>hi;i=exact((__int128)i+step)){if(z.size()>4096)refuse("range limit");z.push_back(Value::integer(i));}return Value::sequence("list",z);}
    if(n=="zip"){std::vector<std::vector<Value>> xs;std::size_t size=4096;for(auto& v:a){xs.push_back(v.items());size=std::min(size,xs.back().size());}std::vector<Value> z;if(a.empty())size=0;for(std::size_t i=0;i<size;++i){std::vector<Value> q;for(auto& x:xs)q.push_back(x[i]);z.push_back(Value::sequence("tuple",q));}return Value::sequence("list",z);}
    if(n=="enumerate"){if(a.empty()||a.size()>2)refuse("enumerate arity");auto xs=a[0].items();std::vector<Value> z;auto start=a.size()==2?a[1].number():0;for(auto& x:xs)z.push_back(Value::sequence("tuple",{Value::integer(start++),x}));return Value::sequence("list",z);}
    if(n=="all"||n=="any"){if(a.size()!=1)refuse("quantifier arity");for(auto& v:a[0].items())if(v.truth()==(n=="any"))return Value::boolean(n=="any");return Value::boolean(n=="all");}
    if(n=="sum"){if(a.empty()||a.size()>2)refuse("sum arity");auto x=a.size()==2?a[1]:Value::integer(0);for(auto& v:a[0].items())x=binary("Add",x,v);return x;}
    if(n=="min"||n=="max"){auto xs=a.size()==1?a[0].items():a;if(xs.empty())refuse("empty extrema");auto z=xs[0];for(auto& x:xs)if(n=="min"?less(x,z):less(z,x))z=x;return z;}
    if(n=="sorted"){if(a.size()!=1)refuse("sort arity");auto xs=a[0].items();auto key=kw.find("key");std::stable_sort(xs.begin(),xs.end(),[&](const Value& x,const Value& y){return key==kw.end()?less(x,y):less(call(key->second,{x}),call(key->second,{y}));});return Value::sequence("list",xs);}
    if(n=="Fraction"){if(a.empty()||a.size()>2)refuse("fraction arity");return fraction(a[0].number(),a.size()==2?a[1].number():1);}
    if(n=="math.gcd"){if(a.size()!=2)refuse("gcd arity");return Value::integer(std::gcd(a[0].number(),a[1].number()));}
    if(n=="re.fullmatch"){if(a.size()!=2)refuse("regex arity");return std::regex_match(a[1].text(),std::regex(a[0].text()))?Value::object("closed_regex_match"):Value::none();}
    refuse("unadmitted builtin:"+n);
}
void Kernel::assign(const json::Value& target,Value v,Environment& e){auto k=tag(target);if(k=="Name"){e[name(target,"id")]=v;return;}if(k=="Attribute"){auto o=evaluate(field(target,"value"),e);o.attribute(name(target,"attr"),v);return;}if(k=="Subscript"){auto o=evaluate(field(target,"value"),e);auto i=evaluate(field(target,"slice"),e);o.put(i,v);return;}if(k=="Tuple"||k=="List"){auto xs=v.items();auto& ts=field(target,"elts").array();if(xs.size()!=ts.size())refuse("unpack extent");for(std::size_t i=0;i<xs.size();++i)assign(ts[i],xs[i],e);return;}refuse("unadmitted assignment:"+k);}
void Kernel::comprehension(const json::Value& j,Environment& e,std::size_t index,std::vector<Value>& z,std::vector<std::pair<Value,Value>>* pairs){const auto& gs=field(j,"generators").array();if(index==gs.size()){if(pairs)pairs->emplace_back(evaluate(field(j,"key"),e),evaluate(field(j,"value"),e));else z.push_back(evaluate(field(j,"elt"),e));return;}auto& g=gs[index];for(auto& x:evaluate(field(g,"iter"),e).items()){consume();assign(field(g,"target"),x,e);bool yes=true;for(auto& c:field(g,"ifs").array())if(!evaluate(c,e).truth()){yes=false;break;}if(yes)comprehension(j,e,index+1,z,pairs);}}
Value Kernel::evaluate(const json::Value& j,Environment& e) {
    consume();auto k=tag(j);
    if(k=="Constant")return fromJson(field(j,"value"));
    if(k=="Name"){auto n=name(j,"id");auto it=e.find(n);if(it!=e.end())return it->second;static const std::set<std::string> types{"str","int","bool","list","tuple","dict","set"};if(types.count(n)){auto x=make("type");x.p->text=n;return x;}static const std::set<std::string> ops{"len","type","isinstance","all","any","range","zip","enumerate","sum","min","max","sorted","deepcopy","uuid4","Fraction","ValueError","Refusal"};if(ops.count(n))return builtin(n);refuse("unadmitted name:"+n);}
    if(k=="Attribute")return attribute(evaluate(field(j,"value"),e),name(j,"attr"));
    if(k=="List"||k=="Tuple"||k=="Set"){std::vector<Value> z;for(auto& a:field(j,"elts").array()){if(tag(a)=="Starred"){auto xs=evaluate(field(a,"value"),e).items();z.insert(z.end(),xs.begin(),xs.end());}else z.push_back(evaluate(a,e));}return Value::sequence(k=="List"?"list":k=="Tuple"?"tuple":"set",z);}
    if(k=="Dict"){auto z=Value::dictionary();auto& ks=field(j,"keys").array();auto& vs=field(j,"values").array();for(std::size_t i=0;i<ks.size();++i){if(ks[i].null()){auto d=evaluate(vs[i],e);for(auto& x:d.p->entries)z.put(x.first,x.second);}else z.put(evaluate(ks[i],e),evaluate(vs[i],e));}return z;}
    if(k=="ListComp"||k=="SetComp"||k=="GeneratorExp"||k=="DictComp"){auto local=e;std::vector<Value> z;std::vector<std::pair<Value,Value>> pairs;comprehension(j,local,0,z,k=="DictComp"?&pairs:nullptr);if(k=="DictComp"){auto d=Value::dictionary();for(auto& x:pairs)d.put(x.first,x.second);return d;}return Value::sequence(k=="SetComp"?"set":"list",z);}
    if(k=="Subscript"){auto v=evaluate(field(j,"value"),e);auto s=field(j,"slice");if(tag(s)!="Slice")return v.get(evaluate(s,e));auto xs=v.items();auto n=static_cast<std::int64_t>(xs.size());auto a=field(s,"lower").null()?0:evaluate(field(s,"lower"),e).number(),b=field(s,"upper").null()?n:evaluate(field(s,"upper"),e).number(),step=field(s,"step").null()?1:evaluate(field(s,"step"),e).number();if(step!=1)refuse("unadmitted slice stride");if(a<0)a+=n;if(b<0)b+=n;a=std::clamp(a,(std::int64_t)0,n);b=std::clamp(b,(std::int64_t)0,n);std::vector<Value> z;for(auto i=a;i<b;++i)z.push_back(xs[i]);if(v.kind()=="string"){std::string out;for(auto& x:z)out+=x.text();return Value::string(out);}return Value::sequence(v.kind(),z);}
    if(k=="Call"){auto f=evaluate(field(j,"func"),e);std::vector<Value> args;for(auto& a:field(j,"args").array()){if(tag(a)=="Starred"){auto xs=evaluate(field(a,"value"),e).items();args.insert(args.end(),xs.begin(),xs.end());}else args.push_back(evaluate(a,e));}std::map<std::string,Value> kw;for(auto& q:field(j,"keywords").array()){if(field(q,"arg").null())refuse("unadmitted arbitrary keywords");kw[name(q,"arg")]=evaluate(field(q,"value"),e);}return call(f,args,kw);}
    if(k=="BoolOp"){auto op=tag(field(j,"op"));Value v;for(auto& x:field(j,"values").array()){v=evaluate(x,e);if(v.truth()==(op=="Or"))return v;}return v;}
    if(k=="UnaryOp"){auto v=evaluate(field(j,"operand"),e);auto op=tag(field(j,"op"));if(op=="Not")return Value::boolean(!v.truth());if(op=="USub")return Value::integer(exact(-(__int128)v.number()));refuse("unadmitted unary");}
    if(k=="BinOp")return binary(tag(field(j,"op")),evaluate(field(j,"left"),e),evaluate(field(j,"right"),e));
    if(k=="Compare"){auto a=evaluate(field(j,"left"),e);auto& ops=field(j,"ops").array();auto& bs=field(j,"comparators").array();for(std::size_t i=0;i<ops.size();++i){auto b=evaluate(bs[i],e);auto op=tag(ops[i]);bool yes;if(op=="Eq"||op=="NotEq")yes=(a==b)==(op=="Eq");else if(op=="Is"||op=="IsNot"){if(a.kind()=="unknown"||b.kind()=="unknown")throw NeedInput{};bool same=a.p==b.p||(a.kind()==b.kind()&&(a.kind()=="none"||a.kind()=="boolean"||a.kind()=="type")&&a==b);yes=same==(op=="Is");}else if(op=="In"||op=="NotIn")yes=b.has(a)==(op=="In");else if(op=="Lt")yes=less(a,b);else if(op=="Gt")yes=less(b,a);else if(op=="LtE")yes=!less(b,a);else if(op=="GtE")yes=!less(a,b);else refuse("unadmitted compare");if(!yes)return Value::boolean(false);a=b;}return Value::boolean(true);}
    if(k=="IfExp")return evaluate(field(j,evaluate(field(j,"test"),e).truth()?"body":"orelse"),e);
    if(k=="Lambda"){auto f=functionValue(j);f.p->closure=std::make_shared<Environment>(e);return f;}
    if(k=="JoinedStr"){std::string s;for(auto& x:field(j,"values").array()){if(tag(x)=="Constant")s+=evaluate(x,e).text();else if(tag(x)=="FormattedValue"){auto v=evaluate(field(x,"value"),e);if(!field(x,"format_spec").null()){auto format=evaluate(field(x,"format_spec"),e).text();if(format!="03d")refuse("unadmitted format spec");std::ostringstream formatted;formatted<<std::setw(3)<<std::setfill('0')<<v.number();s+=formatted.str();}else s+=v.kind()=="string"?v.text():std::to_string(v.number());}else refuse("unadmitted string format");}return Value::string(s);}
    refuse("unadmitted expression:"+k);
}
void Kernel::statements(const json::Value::Array& body,Environment& e) {
    for(auto& j:body){consume();auto k=tag(j);
        if(k=="Expr"){evaluate(field(j,"value"),e);continue;}
        if(k=="Assign"){auto v=evaluate(field(j,"value"),e);for(auto& t:field(j,"targets").array())assign(t,v,e);continue;}
        if(k=="AugAssign"){auto& t=field(j,"target");auto v=binary(tag(field(j,"op")),evaluate(t,e),evaluate(field(j,"value"),e));assign(t,v,e);continue;}
        if(k=="If"){statements(field(j,evaluate(field(j,"test"),e).truth()?"body":"orelse").array(),e);continue;}
        if(k=="For"){for(auto& v:evaluate(field(j,"iter"),e).items()){consume();assign(field(j,"target"),v,e);statements(field(j,"body").array(),e);}statements(field(j,"orelse").array(),e);continue;}
        if(k=="Return")throw Return{field(j,"value").null()?Value::none():evaluate(field(j,"value"),e)};
        if(k=="Raise"){auto v=evaluate(field(j,"exc"),e);refuse(v.text());}
        if(k=="Pass")continue;
        if(k=="FunctionDef"){e[name(j,"name")]=functionValue(j);continue;}
        if(k=="ClassDef"){classes_[name(j,"name")]=j;auto c=make("class");c.p->text=name(j,"name");Environment ce=e;for(auto& q:field(j,"body").array())if(tag(q)=="Assign"){statements(json::Value::Array{q},ce);for(auto& t:field(q,"targets").array())if(tag(t)=="Name")c.p->attributes[name(t,"id")]=ce.at(name(t,"id"));}e[c.p->text]=c;continue;}
        if(k=="Import"||k=="ImportFrom"){if(k=="Import"){for(auto& q:field(j,"names").array()){auto n=name(q,"name");if(n!="copy"&&n!="math"&&n!="re")refuse("unadmitted import:"+n);auto v=make("namespace");v.p->text=n;e[n]=v;}}else{auto n=name(j,"module");if(n!="copy"&&n!="uuid"&&n!="fractions")refuse("unadmitted from import");for(auto& q:field(j,"names").array()){auto a=name(q,"name");if(a!="deepcopy"&&a!="uuid4"&&a!="Fraction")refuse("unadmitted imported symbol");e[a]=builtin(a);}}continue;}
        refuse("unadmitted statement:"+k);
    }
}
} // namespace fathom::tasks::ear234::closed
