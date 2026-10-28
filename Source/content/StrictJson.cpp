#include "content/StrictJson.hpp"
#include <charconv>
#include <cmath>
#include <iomanip>
#include <locale>
#include <sstream>

namespace fathom::json {
Value Value::fromInteger(std::int64_t n) { return Number{std::to_string(n)}; }
bool Value::integer(std::int64_t& n) const noexcept {
    if (!isNumber()) return false;
    const auto& s = std::get<Number>(data).token;
    const auto r = std::from_chars(s.data(), s.data() + s.size(), n);
    return r.ec == std::errc{} && r.ptr == s.data() + s.size();
}
const Value* Value::find(const std::string& key) const {
    if (!isObject()) return nullptr;
    const auto it = object().find(key);
    return it == object().end() ? nullptr : &it->second;
}
Error::Error(std::string c, std::size_t n, const std::string& m)
    : std::runtime_error(m), code(std::move(c)), offset(n) {}
namespace {
class Parser {
    const std::string& s;
    const Limits& limits;
    std::size_t pos = 0, count = 0;
    [[noreturn]] void fail(const char* code, const char* message) const { throw Error(code, pos, message); }
    void whitespace() { while (pos < s.size() && (s[pos]==' ' || s[pos]=='\t' || s[pos]=='\r' || s[pos]=='\n')) ++pos; }
    bool take(char c) { if (pos < s.size() && s[pos] == c) { ++pos; return true; } return false; }
    unsigned hex() {
        unsigned n = 0;
        for (int i=0;i<4;++i) {
            if (pos == s.size()) fail("JSON_ESCAPE", "Incomplete Unicode escape");
            const char c=s[pos++];
            unsigned d;
            if (c>='0'&&c<='9') d=static_cast<unsigned>(c-'0');
            else if(c>='a'&&c<='f') d=static_cast<unsigned>(c-'a'+10);
            else if(c>='A'&&c<='F') d=static_cast<unsigned>(c-'A'+10);
            else fail("JSON_ESCAPE", "Invalid Unicode hex digit");
            n=(n<<4)|d;
        }
        return n;
    }
    static void utf8(std::string& out, unsigned cp) {
        if(cp<0x80) out+=static_cast<char>(cp);
        else if(cp<0x800) { out+=static_cast<char>(0xc0|(cp>>6)); out+=static_cast<char>(0x80|(cp&63)); }
        else if(cp<0x10000) { out+=static_cast<char>(0xe0|(cp>>12)); out+=static_cast<char>(0x80|((cp>>6)&63)); out+=static_cast<char>(0x80|(cp&63)); }
        else { out+=static_cast<char>(0xf0|(cp>>18)); out+=static_cast<char>(0x80|((cp>>12)&63)); out+=static_cast<char>(0x80|((cp>>6)&63)); out+=static_cast<char>(0x80|(cp&63)); }
    }
    std::string string() {
        if(!take('"')) fail("JSON_SYNTAX", "Expected string");
        std::string out;
        while(pos<s.size()) {
            const auto c=static_cast<unsigned char>(s[pos++]);
            if(c=='"') return out;
            if(c<0x20) fail("JSON_STRING", "Unescaped control character");
            if(c=='\\') {
                if(pos==s.size()) fail("JSON_ESCAPE", "Incomplete escape");
                switch(s[pos++]) {
                    case '"': out+='"'; break; case '\\': out+='\\'; break; case '/': out+='/'; break;
                    case 'b': out+='\b'; break; case 'f': out+='\f'; break; case 'n': out+='\n'; break;
                    case 'r': out+='\r'; break; case 't': out+='\t'; break;
                    case 'u': {
                        unsigned cp=hex();
                        if(cp>=0xd800&&cp<=0xdbff) {
                            if(!take('\\')||!take('u')) fail("JSON_SURROGATE", "Unpaired high surrogate");
                            const unsigned low=hex();
                            if(low<0xdc00||low>0xdfff) fail("JSON_SURROGATE", "Invalid low surrogate");
                            cp=0x10000+((cp-0xd800)<<10)+(low-0xdc00);
                        } else if(cp>=0xdc00&&cp<=0xdfff) fail("JSON_SURROGATE", "Unpaired low surrogate");
                        utf8(out,cp); break;
                    }
                    default: fail("JSON_ESCAPE", "Unknown escape");
                }
            } else if(c<0x80) out+=static_cast<char>(c);
            else {
                unsigned cp=0, n=0, minimum=0;
                if(c>=0xc2&&c<=0xdf) {cp=c&31; n=1; minimum=0x80;}
                else if(c>=0xe0&&c<=0xef) {cp=c&15; n=2; minimum=0x800;}
                else if(c>=0xf0&&c<=0xf4) {cp=c&7; n=3; minimum=0x10000;}
                else fail("JSON_UTF8", "Invalid UTF-8 leading byte");
                for(unsigned i=0;i<n;++i) {
                    if(pos==s.size()) fail("JSON_UTF8", "Truncated UTF-8");
                    const auto d=static_cast<unsigned char>(s[pos++]);
                    if((d&0xc0)!=0x80) fail("JSON_UTF8", "Invalid UTF-8 continuation");
                    cp=(cp<<6)|(d&63);
                }
                if(cp<minimum || cp>0x10ffff || (cp>=0xd800&&cp<=0xdfff)) fail("JSON_UTF8", "Invalid Unicode scalar");
                utf8(out,cp);
            }
            if(out.size()>limits.stringBytes) fail("JSON_STRING_LIMIT", "Decoded string exceeds limit");
        }
        fail("JSON_STRING", "Unterminated string");
    }
    Value number() {
        const auto begin=pos;
        take('-');
        if(take('0')) { if(pos<s.size()&&s[pos]>='0'&&s[pos]<='9') fail("JSON_NUMBER", "Leading zero"); }
        else {
            if(pos==s.size()||s[pos]<'1'||s[pos]>'9') fail("JSON_NUMBER", "Expected integer digits");
            while(pos<s.size()&&s[pos]>='0'&&s[pos]<='9') ++pos;
        }
        if(take('.')) {
            const auto digits=pos;
            while(pos<s.size()&&s[pos]>='0'&&s[pos]<='9') ++pos;
            if(digits==pos) fail("JSON_NUMBER", "Missing fractional digits");
        }
        if(take('e')||take('E')) {
            if(!take('+')) take('-');
            const auto digits=pos;
            while(pos<s.size()&&s[pos]>='0'&&s[pos]<='9') ++pos;
            if(digits==pos) fail("JSON_NUMBER", "Missing exponent digits");
        }
        if(pos-begin>limits.numberBytes) fail("JSON_NUMBER_LIMIT", "Number token exceeds limit");
        const auto token=s.substr(begin,pos-begin);
        // A complete int64 token is necessarily finite; retain its exact spelling.
        // Decimals, exponents and overflow keep the original double-range check.
        std::int64_t integer=0;
        const auto parsed=std::from_chars(token.data(),token.data()+token.size(),integer);
        if(parsed.ec==std::errc{} && parsed.ptr==token.data()+token.size()) return Number{token};
        std::istringstream in(token); in.imbue(std::locale::classic()); double n=0; in>>n;
        if(in.fail() || !std::isfinite(n)) fail("JSON_NONFINITE", "Number outside finite double range");
        return Number{token};
    }
    Value value(std::size_t depth) {
        whitespace();
        if(depth>limits.depth) fail("JSON_DEPTH_LIMIT", "Nesting exceeds limit");
        if(++count>limits.values) fail("JSON_VALUE_LIMIT", "Value count exceeds limit");
        if(pos==s.size()) fail("JSON_SYNTAX", "Expected value");
        if(s[pos]=='"') return string();
        if(take('{')) {
            Value::Object o; whitespace(); if(take('}')) return o;
            do {
                whitespace(); const auto key=string(); whitespace();
                if(!take(':')) fail("JSON_SYNTAX", "Expected colon");
                if(o.count(key)) fail("JSON_DUPLICATE_KEY", "Duplicate decoded object key");
                o.emplace(key,value(depth+1)); whitespace();
                if(take('}')) return o;
            } while(take(','));
            fail("JSON_SYNTAX", "Expected comma or object end");
        }
        if(take('[')) {
            Value::Array a; whitespace(); if(take(']')) return a;
            do { a.push_back(value(depth+1)); whitespace(); if(take(']')) return a; } while(take(','));
            fail("JSON_SYNTAX", "Expected comma or array end");
        }
        for(const auto& literal: {std::string("true"),std::string("false"),std::string("null")}) {
            if(s.compare(pos,literal.size(),literal)==0) { pos+=literal.size(); if(literal=="null") return nullptr; return literal=="true"; }
        }
        if(s[pos]=='-'||(s[pos]>='0'&&s[pos]<='9')) return number();
        fail("JSON_SYNTAX", "Unknown JSON value");
    }
public:
    Parser(const std::string& input,const Limits& l):s(input),limits(l) {}
    Value run() {
        if(s.size()>limits.bytes) fail("JSON_BYTE_LIMIT", "Document exceeds limit");
        auto result=value(0); whitespace();
        if(pos!=s.size()) fail("JSON_TRAILING", "Trailing data");
        return result;
    }
};
std::string quote(const std::string& s) {
    std::ostringstream out; out.imbue(std::locale::classic()); out<<'"';
    for(unsigned char c:s) {
        if(c=='"') out<<"\\\""; else if(c=='\\') out<<"\\\\";
        else if(c<32) out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<static_cast<unsigned>(c);
        else out<<static_cast<char>(c);
    }
    out<<'"'; return out.str();
}
} // namespace
Value parse(const std::string& s,const Limits& l) { return Parser(s,l).run(); }
std::string stringify(const Value& v) {
    if(v.null()) return "null";
    if(v.isBool()) return v.boolean()?"true":"false";
    if(v.isNumber()) return std::get<Number>(v.data).token;
    if(v.isString()) return quote(v.string());
    std::string out; bool first=true;
    if(v.isArray()) { out="["; for(const auto& e:v.array()) { if(!first) out+=','; first=false; out+=stringify(e); } return out+"]"; }
    out="{"; for(const auto& kv:v.object()) { if(!first) out+=','; first=false; out+=quote(kv.first)+":"+stringify(kv.second); } return out+"}";
}
} // namespace fathom::json
