#include "metronome/MetronomePreferences.hpp"
#include "storage/StorageEnvelope.hpp"
#include <algorithm>
#include <set>

namespace fathom::metronome {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
void need(bool yes,const char* why){if(!yes)throw std::invalid_argument(why);}
const V& field(const V& v,const std::string& key){need(v.isObject()&&v.find(key),"Missing timing field; preserve value and select a supported configuration");return *v.find(key);}
void shape(const V& v,std::initializer_list<const char*> keys){need(v.isObject()&&v.object().size()==keys.size(),"Unsupported timing shape/version; preserve value and choose a supported version");for(auto key:keys)need(v.find(key),"Missing timing field");}
int number(const V& v,int lo,int hi){std::int64_t n{};need(v.integer(n)&&n>=lo&&n<=hi,"Timing value requires a supported exact integer");return static_cast<int>(n);}
bool boolean(const V& v){need(v.isBool(),"Timing flag must be boolean");return v.boolean();}
std::string text(const V& v){need(v.isString(),"Timing text must be a string");return v.string();}
V n(int v){return V::fromInteger(v);}
int choice(const V& v,std::initializer_list<const char*> choices){auto s=text(v);int i=0;for(auto t:choices){if(s==t)return i;++i;}throw std::invalid_argument("Unsupported timing choice; preserve original and choose supported value");}
std::size_t scalars(const std::string& s){
    std::size_t count=0;
    for(std::size_t i=0;i<s.size();){
        const auto first=static_cast<unsigned char>(s[i++]);std::uint32_t code{};int more{};
        if(first<0x80){code=first;more=0;}
        else if(first>=0xc2&&first<=0xdf){code=first&0x1f;more=1;}
        else if(first>=0xe0&&first<=0xef){code=first&0x0f;more=2;}
        else if(first>=0xf0&&first<=0xf4){code=first&0x07;more=3;}
        else throw std::invalid_argument("Preset name requires valid UTF-8");
        for(int j=0;j<more;++j){need(i<s.size(),"Truncated UTF-8 preset name");auto b=static_cast<unsigned char>(s[i++]);need((b&0xc0)==0x80,"Invalid UTF-8 continuation");code=(code<<6)|(b&0x3f);}
        need((more!=1||code>=0x80)&&(more!=2||code>=0x800)&&(more!=3||code>=0x10000)&&code<=0x10ffff&&!(code>=0xd800&&code<=0xdfff),"Invalid UTF-8 scalar");++count;
    }return count;
}
void validPreset(const Preset& p){storage::validateUuid(p.id);auto count=scalars(p.name);need(count>=1&&count<=64,"Preset name requires 1–64 Unicode characters");validate(p.settings);}
void validPreferences(const Preferences& p){validate(p.lastUsed);need(p.presets.size()<=32,"At most 32 local presets; replace an explicit existing ID or remove one");std::set<std::string> seen;for(const auto& preset:p.presets){validPreset(preset);need(seen.insert(preset.id).second,"Duplicate preset identity");}}
}
Settings decodeSettings(const V& v){
    shape(v,{"tempo","beat_unit_q","meter","subdivision","styles","metronome_enabled","polyrhythm_enabled","x","y","reference","count_in","ramp","master_volume","volumes","mute","solo","master_mute"});
    Settings s;s.tempo=number(field(v,"tempo"),20,300);const auto& unit=field(v,"beat_unit_q");
    need(unit.isArray()&&unit.array().size()==2,"Exact BPM reference pair required");int un=number(unit.array()[0],1,3),ud=number(unit.array()[1],1,2);
    if(un==1&&ud==2)s.unit=scheduler::BeatUnit::Eighth;else if(un==1&&ud==1)s.unit=scheduler::BeatUnit::Quarter;else if(un==3&&ud==2)s.unit=scheduler::BeatUnit::DottedQuarter;else if(un==2&&ud==1)s.unit=scheduler::BeatUnit::Half;else throw std::invalid_argument("Unsupported BPM reference; do not normalize unsupported persisted pairs");
    const auto& meter=field(v,"meter");need(meter.isArray()&&meter.array().size()==2,"Explicit meter pair required");s.numerator=number(meter.array()[0],1,16);s.denominator=number(meter.array()[1],2,16);s.subdivision=number(field(v,"subdivision"),1,7);
    const auto& styles=field(v,"styles");need(styles.isArray()&&styles.array().size()==static_cast<std::size_t>(s.numerator),"One style per meter denominator beat required");s.styles.clear();for(const auto& item:styles.array())s.styles.push_back(static_cast<Style>(choice(item,{"accent","normal","silent"})));
    s.metronomeEnabled=boolean(field(v,"metronome_enabled"));s.polyrhythmEnabled=boolean(field(v,"polyrhythm_enabled"));s.masterMute=boolean(field(v,"master_mute"));s.masterVolume=number(field(v,"master_volume"),0,100);s.x=number(field(v,"x"),1,16);s.y=number(field(v,"y"),1,16);s.reference=static_cast<Reference>(choice(field(v,"reference"),{"A","B","Cycle"}));s.countIn=static_cast<CountIn>(choice(field(v,"count_in"),{"configured_bar","authored_bar","Off"}));
    const auto& vols=field(v,"volumes");shape(vols,{"reference","metronome","A","B"});int index=0;for(auto key:{"reference","metronome","A","B"})s.volumes[static_cast<std::size_t>(index++)]=number(field(vols,key),0,100);
    const auto& mute=field(v,"mute");const auto& solo=field(v,"solo");shape(mute,{"A","B"});shape(solo,{"A","B"});s.mute={boolean(field(mute,"A")),boolean(field(mute,"B"))};s.solo={boolean(field(solo,"A")),boolean(field(solo,"B"))};
    const auto& ramp=field(v,"ramp");if(!ramp.null()){shape(ramp,{"direction","step","every","target"});s.ramp=Ramp{choice(field(ramp,"direction"),{"up","down"})==0,number(field(ramp,"step"),1,20),number(field(ramp,"every"),1,32),number(field(ramp,"target"),20,300)};}
    validate(s);return s;
}
V encodeSettings(const Settings& s){
    validate(s);static const std::array<std::pair<int,int>,4> units{{{1,2},{1,1},{3,2},{2,1}}};auto u=units[static_cast<std::size_t>(s.unit)];
    A styles;for(auto style:s.styles)styles.push_back(style==Style::Accent?"accent":style==Style::Normal?"normal":"silent");V ramp=nullptr;if(s.ramp){const auto& r=*s.ramp;ramp=O{{"direction",r.up?"up":"down"},{"step",n(r.step)},{"every",n(r.every)},{"target",n(r.target)}};}
    return O{{"tempo",n(s.tempo)},{"beat_unit_q",A{n(u.first),n(u.second)}},{"meter",A{n(s.numerator),n(s.denominator)}},{"subdivision",n(s.subdivision)},{"styles",styles},{"metronome_enabled",s.metronomeEnabled},{"polyrhythm_enabled",s.polyrhythmEnabled},{"master_mute",s.masterMute},{"x",n(s.x)},{"y",n(s.y)},{"reference",s.reference==Reference::A?"A":s.reference==Reference::B?"B":"Cycle"},{"count_in",s.countIn==CountIn::ConfiguredBar?"configured_bar":s.countIn==CountIn::AuthoredBar?"authored_bar":"Off"},{"ramp",ramp},{"master_volume",n(s.masterVolume)},{"volumes",O{{"reference",n(s.volumes[0])},{"metronome",n(s.volumes[1])},{"A",n(s.volumes[2])},{"B",n(s.volumes[3])}}},{"mute",O{{"A",s.mute[0]},{"B",s.mute[1]}}},{"solo",O{{"A",s.solo[0]},{"B",s.solo[1]}}}};
}
Preferences decodePreferences(const V& v){
    shape(v,{"version","last_used","presets"});need(text(field(v,"version"))=="timing-initial1","Unknown timing preference version; preserve and choose a supported version");Preferences p;p.lastUsed=decodeSettings(field(v,"last_used"));const auto& presets=field(v,"presets");need(presets.isArray()&&presets.array().size()<=32,"At most32 presets required");
    for(const auto& item:presets.array()){shape(item,{"id","name","version","settings"});need(number(field(item,"version"),1,1)==1,"Unsupported preset version");p.presets.push_back({text(field(item,"id")),text(field(item,"name")),decodeSettings(field(item,"settings"))});}validPreferences(p);return p;
}
V encodePreferences(const Preferences& p){validPreferences(p);A presets;for(const auto& v:p.presets)presets.push_back(O{{"id",v.id},{"name",v.name},{"version",n(1)},{"settings",encodeSettings(v.settings)}});return O{{"version","timing-initial1"},{"last_used",encodeSettings(p.lastUsed)},{"presets",presets}};}
bool preferenceValidator(const std::string& key,std::int64_t version,const V& v) noexcept {
    if((key!="freeplay_timing"&&key!="lesson_timing")||version!=1)return false;
    try{decodePreferences(v);return true;}catch(...){return false;}
}
void putPreset(Preferences& p,std::string id,std::string name,Settings s,bool replace){
    validPreferences(p);Preset next{std::move(id),std::move(name),std::move(s)};validPreset(next);auto found=std::find_if(p.presets.begin(),p.presets.end(),[&](const auto& item){return item.id==next.id;});
    if(replace){need(found!=p.presets.end(),"Replacement requires an existing explicit preset ID");*found=std::move(next);}
    else{need(found==p.presets.end(),"Preset ID already exists; use explicit Replace");need(p.presets.size()<32,"Preset limit32 reached; select an explicit replacement");p.presets.push_back(std::move(next));}
}
Settings restoreLastUsed(const Preferences& p,bool stopped){need(stopped,"Stop and resolve the current outcome before restoring timing settings");validPreferences(p);return p.lastUsed;}
Settings restorePreset(const Preferences& p,const std::string& id,bool stopped){need(stopped,"Stop and resolve the current outcome before restoring a preset");validPreferences(p);auto found=std::find_if(p.presets.begin(),p.presets.end(),[&](const auto& item){return item.id==id;});need(found!=p.presets.end(),"Preset ID is unavailable; select an existing preset");return found->settings;}
}
