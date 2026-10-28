#include "desktop/TypedManualForm.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <stdexcept>
#include <limits>

namespace fathom::desktop {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
struct FormError final : std::runtime_error { explicit FormError(const char* reason):std::runtime_error(reason){} };
juce::String ju(const std::string& s){return juce::String::fromUTF8(s.c_str());}
const V& f(const V& v,const char* key){const auto* p=v.find(key);if(!p)throw FormError("Missing learner form field");return *p;}
std::int64_t integer(const V& v){std::int64_t n{};if(!v.integer(n))throw FormError("Expected an integer form bound");return n;}
// Compare finite decimal tokens without converting their reported precision to
// binary floating point. StrictJson owns syntax, size and finite-number limits.
struct Decimal { bool negative{};std::string digits;std::int64_t power{}; };
V finiteNumber(const std::string& raw){
    V value;try{value=json::parse(raw);}catch(...){throw FormError("Enter one finite JSON number");}
    if(!value.isNumber()||std::get<json::Number>(value.data).token!=raw)throw FormError("Enter one finite JSON number");return value;
}
Decimal decimal(const V& value){
    if(!value.isNumber())throw FormError("Expected a finite numeric form bound");
    const auto raw=std::get<json::Number>(value.data).token;finiteNumber(raw);Decimal out;out.negative=raw[0]=='-';
    const auto start=out.negative?std::size_t{1}:std::size_t{0};const auto e=raw.find_first_of("eE",start);const auto end=e==std::string::npos?raw.size():e;const auto dot=raw.find('.',start);
    for(auto n=start;n<end;++n)if(raw[n]!='.')out.digits+=raw[n];
    const auto first=out.digits.find_first_not_of('0');if(first==std::string::npos){out.digits="0";out.negative=false;return out;}out.digits.erase(0,first);
    std::int64_t exponent{};if(e!=std::string::npos){try{exponent=std::stoll(raw.substr(e+1));}catch(...){throw FormError("Numeric exponent outside the finite form domain");}}
    // A nonzero token accepted by StrictJson's finite domain cannot approach
    // these integer limits; check before combining the bounded coefficient.
    if(exponent < -4096 || exponent > 4096)throw FormError("Numeric exponent outside the finite form domain");
    out.power=exponent-(dot!=std::string::npos&&dot<end?static_cast<std::int64_t>(end-dot-1):0);
    while(out.digits.size()>1&&out.digits.back()=='0'){out.digits.pop_back();++out.power;}return out;
}
int compareNumbers(const V& a,const V& b){
    const auto x=decimal(a),y=decimal(b);if(x.negative!=y.negative)return x.negative?-1:1;
    int order{};if(x.digits=="0"||y.digits=="0")order=x.digits==y.digits?0:(x.digits=="0"?-1:1);
    else{const auto xMagnitude=static_cast<std::int64_t>(x.digits.size())+x.power,yMagnitude=static_cast<std::int64_t>(y.digits.size())+y.power;
        if(xMagnitude!=yMagnitude)order=xMagnitude<yMagnitude?-1:1;
        else for(std::size_t n=0;n<std::max(x.digits.size(),y.digits.size());++n){const char xd=n<x.digits.size()?x.digits[n]:'0',yd=n<y.digits.size()?y.digits[n]:'0';if(xd!=yd){order=xd<yd?-1:1;break;}}
    }return x.negative?-order:order;
}
std::string type(const V& s){const auto* t=s.find("type");if(!t)return {};if(t->isString())return t->string();if(!t->isArray())throw FormError("Invalid learner form type");for(const auto& v:t->array())if(v.isString()&&v.string()!="null")return v.string();return {};}
bool nullable(const V& s){const auto* p=s.find("type");return p&&p->isArray()&&std::find(p->array().begin(),p->array().end(),V("null"))!=p->array().end();}
std::string human(std::string text){std::replace(text.begin(),text.end(),'_',' ');if(!text.empty())text[0]=static_cast<char>(std::toupper(static_cast<unsigned char>(text[0])));return text;}
std::string label(const V& schema,const std::string& fallback){const auto* p=schema.find("label");return p&&p->isString()?p->string():human(fallback);}
std::string valueLabel(const V& v){if(v.null())return "Unknown / not supplied";if(v.isString())return v.string();if(v.isBool())return v.boolean()?"Yes":"No";if(v.isNumber())return std::get<json::Number>(finiteNumber(std::get<json::Number>(v.data).token).data).token;if(v.isObject()&&v.find("string")&&v.find("fret")){const auto& sourceString=f(v,"string");const auto name=sourceString.isString()?sourceString.string():std::to_string(integer(sourceString));return "String "+name+", fret "+std::to_string(integer(f(v,"fret")));}if(v.isArray())return std::to_string(v.array().size())+" explicit entries";return "Earlier explicit structured choice";}
std::string bindingLabel(const V& schema,const V& value){
    const auto* choices=schema.find("enum");const auto* labels=schema.find("enumLabels");if(choices&&labels){if(!choices->isArray()||!labels->isArray()||choices->array().size()!=labels->array().size())throw FormError("Choice labels must exactly match the finite domain");for(std::size_t n=0;n<choices->array().size();++n)if(choices->array()[n]==value){if(!labels->array()[n].isString())throw FormError("Choice labels must be readable text");return labels->array()[n].string();}}
    return valueLabel(value);
}
std::string preview(const std::string& text){std::size_t end=std::min(text.size(),std::size_t{160});while(end<text.size()&&end>0&&(static_cast<unsigned char>(text[end])&0xc0)==0x80)--end;auto out=text.substr(0,end);std::replace(out.begin(),out.end(),'\n',' ');std::replace(out.begin(),out.end(),'\r',' ');if(end<text.size())out+=" … (full report retained by owner)";return out;}
void checkbox(juce::ToggleButton& c,const std::string& id,const std::string& text){c.setComponentID(ju(id));c.setButtonText(ju(text));c.setColour(juce::ToggleButton::textColourId,juce::Colour(0xff182b33));c.setColour(juce::ToggleButton::tickColourId,juce::Colour(0xff182b33));c.setColour(juce::ToggleButton::tickDisabledColourId,juce::Colour(0xff586b73));}
}
namespace manual_text {
void configureReadOnly(juce::TextEditor& editor,const char* id,const char* title){
    editor.setComponentID(id);editor.setTitle(title);editor.setMultiLine(true,true);
    editor.setReadOnly(true);editor.setScrollbarsShown(true);editor.setWantsKeyboardFocus(true);
    editor.setFont(juce::FontOptions{16.0f});
}
void setReadOnlyText(juce::TextEditor& editor,const juce::String& text){
    if(editor.getText()!=text)editor.setText(text,false);
    // JUCE retains its native text interface. Help/description also exposes
    // the permitted text to clients which request only a static-text name.
    editor.setDescription(text);editor.setTooltip(text);
}
int labelHeight(juce::Label& label,int width,int minimum){
    label.setJustificationType(juce::Justification::topLeft);
    label.setMinimumHorizontalScale(1.0f);label.setTitle(label.getText());label.setTooltip(label.getText());
    juce::AttributedString text(label.getText());text.setFont(label.getFont());
    juce::TextLayout layout;layout.createLayout(text,static_cast<float>(std::max(1,width-8)));
    return std::max(minimum,static_cast<int>(std::ceil(layout.getHeight()))+8);
}
int toggleHeight(juce::ToggleButton& toggle,int width,int minimum){
    toggle.setTitle(toggle.getButtonText());toggle.setTooltip(toggle.getButtonText());
    juce::AttributedString text(toggle.getButtonText());text.setFont(juce::FontOptions{15.0f});
    juce::TextLayout layout;layout.createLayout(text,static_cast<float>(std::max(1,width-28)));
    return std::max(minimum,static_cast<int>(std::ceil(layout.getHeight()))+8);
}
std::string releaseGuidance(bool physicalReleaseRequired,bool externalStopRequired){
    std::string text;
    if(physicalReleaseRequired)text+="Release your instrument as instructed, then confirm the release.\n";
    if(externalStopRequired)text+="Stop the external sound source, then confirm it has stopped.\n";
    if(text.empty())text="No physical release or external source stop is required right now.\n";
    return text;
}
int textHeight(const juce::TextEditor& editor,int width,int minimum){
    juce::AttributedString text(editor.getText());text.setFont(editor.getFont());
    juce::TextLayout layout;layout.createLayout(text,static_cast<float>(std::max(1,width-20)));
    return std::max(minimum,static_cast<int>(std::ceil(layout.getHeight()))+16);
}
}
struct TypedManualForm::Field {
    V schema;std::string path,name,kind;std::uint64_t serial{};
    std::vector<std::unique_ptr<Field>> children;std::vector<V> choices;
    std::unique_ptr<juce::Label> label;
    std::unique_ptr<juce::TextEditor> text;
    std::unique_ptr<juce::ComboBox> choice,count;
    std::unique_ptr<juce::TextEditor> countInput;
    std::unique_ptr<juce::TextButton> countApply;
    std::unique_ptr<juce::Label> countError;
    bool explicitCountReady{};
    std::unique_ptr<juce::ToggleButton> ack,unknown,include;
};
// Bound text layout per page; original committed UTF-8 text stays complete.
struct TypedManualForm::ReportPanel final:juce::Component {
    ReadOnlyTextEditor text;juce::Label page;juce::TextButton previous{"Previous"},next{"Next"};std::string full;std::vector<std::size_t> starts;std::size_t current{};
    ReportPanel(){setComponentID("committed-reports-panel");manual_text::configureReadOnly(text,"committed-report-page","Committed reports; full text is available through numbered pages");for(auto*c:std::initializer_list<juce::Component*>{&text,&page,&previous,&next})addAndMakeVisible(*c);previous.setComponentID("committed-reports-previous");next.setComponentID("committed-reports-next");previous.setTitle("Previous committed report page");next.setTitle("Next committed report page");previous.setWantsKeyboardFocus(true);next.setWantsKeyboardFocus(true);page.setComponentID("committed-reports-page-number");page.setColour(juce::Label::textColourId,juce::Colour(0xff182b33));page.setJustificationType(juce::Justification::centred);previous.onClick=[this]{if(current){--current;refresh();}};next.onClick=[this]{if(current+1<starts.size()){++current;refresh();}};}
    void set(std::string value){if(value==full)return;full=std::move(value);starts.clear();current=0;std::size_t offset=0;while(offset<full.size()){starts.push_back(offset);auto end=std::min(offset+8192,full.size());while(end<full.size()&&end>offset&&(static_cast<unsigned char>(full[end])&0xc0)==0x80)--end;offset=end;}refresh();}
    void refresh(){const auto end=current+1<starts.size()?starts[current+1]:full.size();const auto shown=starts.empty()?std::string{}:full.substr(starts[current],end-starts[current]);manual_text::setReadOnlyText(text,ju(shown));text.moveCaretToTop(false);previous.setEnabled(current>0);next.setEnabled(current+1<starts.size());page.setText("Committed reports - page "+ju(std::to_string(starts.empty()?0:current+1))+" of "+ju(std::to_string(starts.size())),juce::dontSendNotification);}
    void resized()override{auto r=getLocalBounds();auto nav=r.removeFromTop(30);previous.setBounds(nav.removeFromLeft(92).reduced(2));next.setBounds(nav.removeFromRight(92).reduced(2));page.setBounds(nav);text.setBounds(r);}
};
TypedManualForm::TypedManualForm(){reports_=std::make_unique<ReportPanel>();addChildComponent(*reports_);setComponentID("typed-manual-form");manual_text::configureReadOnly(instructions_,"typed-instructions","Instructions");manual_text::configureReadOnly(history_,"typed-history","Your reported actions");viewport_.setComponentID("typed-viewport");viewport_.setTitle("Your report fields; scroll to reach all fields");body_.setComponentID("typed-body");viewport_.setViewedComponent(&body_,false);viewport_.setScrollBarsShown(true,false);addAndMakeVisible(instructions_);addAndMakeVisible(history_);addAndMakeVisible(viewport_);}
TypedManualForm::~TypedManualForm()=default;
bool TypedManualForm::current()const noexcept{try{return ownerIsCurrent_&&ownerIsCurrent_();}catch(...){return false;}}
std::uint64_t TypedManualForm::configure(const V& s,const std::vector<std::string>& text,std::function<bool()> fence){
    if(!fence||!fence())throw FormError("A current native owner action is required");++generation_;ownerIsCurrent_=std::move(fence);form_.reset();schema_=nullptr;
    try{form_=build(s,"input","Your report");schema_=s;setInstructions(text);viewport_.setViewPosition(0,0);resized();return generation_;}catch(...){form_.reset();ownerIsCurrent_={};throw;}
}
void TypedManualForm::invalidate(){++generation_;ownerIsCurrent_={};}
bool TypedManualForm::sameField(std::uint64_t serial,const std::string& path)const{if(!form_)return false;const auto* field=find(*form_,path);return field&&field->serial==serial;}
void TypedManualForm::changed(std::uint64_t generation,const std::string& path,std::uint64_t serial){if(generation!=generation_||!current()||!sameField(serial,path))return;const auto cb=onEdited;if(cb)cb(path);}
void TypedManualForm::wire(Field& field){const auto generation=generation_;const auto path=field.path;const auto serial=field.serial;juce::Component::SafePointer<TypedManualForm> safe(this);auto notify=[safe,generation,path,serial]{if(safe)safe->changed(generation,path,serial);};if(field.choice)field.choice->onChange=notify;if(field.text)field.text->onTextChange=notify;if(field.ack)field.ack->onClick=notify;if(field.unknown)field.unknown->onClick=notify;if(field.include)field.include->onClick=notify;}
std::unique_ptr<TypedManualForm::Field> TypedManualForm::build(const V& schema,const std::string& path,const std::string& name,bool optional){
    if(schema.find("default"))throw FormError("Learner defaults are not allowed");auto p=std::make_unique<Field>();p->schema=schema;p->serial=fieldSerial_++;p->path=path;p->name=name;p->label=std::make_unique<juce::Label>();p->label->setComponentID(ju("typed-label-"+path));p->label->setColour(juce::Label::textColourId,juce::Colour(0xff182b33));p->label->setText(ju(label(schema,name)),juce::dontSendNotification);body_.addAndMakeVisible(*p->label);
    if(optional){p->include=std::make_unique<juce::ToggleButton>();checkbox(*p->include,"typed-include-"+path,"Include my optional "+label(schema,name));body_.addAndMakeVisible(*p->include);}
    if(const auto* constant=schema.find("const")){const auto* origin=schema.find("literal_binding_label");if(!origin||!origin->isString())throw FormError("Source / prior-choice bindings must be labeled");p->kind="constant";const bool identity=name=="key"||name=="source_key"||name.find("sha256")!=std::string::npos;const auto title=identity?"Current verified task binding":label(schema,name)+" — "+bindingLabel(schema,*constant);p->label->setText(ju((origin->string()=="source_protocol_binding"?"Printed / protocol binding: ":"Your earlier explicit choice: ")+title),juce::dontSendNotification);wire(*p);return p;}
    p->kind=type(schema);if(const auto* choices=schema.find("enum")){if(!choices->isArray()||choices->array().empty())throw FormError("A finite choice domain is required");p->kind="enum";p->choices=choices->array();}
    else if(p->kind=="boolean"&&(nullable(schema)||!schema.find("must_be"))){p->kind="enum";p->choices={true,false};if(nullable(schema))p->choices.emplace_back(nullptr);}
    if(nullable(schema)&&(p->kind=="object"||p->kind=="array")){p->unknown=std::make_unique<juce::ToggleButton>();checkbox(*p->unknown,"typed-unknown-"+path,"Unknown / not supplied");body_.addAndMakeVisible(*p->unknown);}
    if(p->kind=="enum"){p->choice=std::make_unique<juce::ComboBox>();p->choice->setComponentID(ju("typed-field-"+path));p->choice->setTextWhenNothingSelected("Choose explicitly");const auto* names=schema.find("enumLabels");if(names&&(!names->isArray()||names->array().size()!=p->choices.size()))throw FormError("Choice labels must exactly match the finite domain");for(std::size_t n=0;n<p->choices.size();++n){if(names&&!names->array()[n].isString())throw FormError("Choice labels must be readable text");p->choice->addItem(ju(names?names->array()[n].string():valueLabel(p->choices[n])),static_cast<int>(n+1));}body_.addAndMakeVisible(*p->choice);}
    else if(p->kind=="object"){const auto& properties=f(schema,"properties").object();const auto& required=f(schema,"required").array();if(!schema.find("additionalProperties")||f(schema,"additionalProperties")!=V(false))throw FormError("Exact object fields are required");for(const auto& r:required)if(!r.isString()||properties.find(r.string())==properties.end())throw FormError("Required form field is outside the object");for(const auto& item:properties)p->children.push_back(build(item.second,path+"/"+item.first,item.first,std::find(required.begin(),required.end(),V(item.first))==required.end()));}
    else if(p->kind=="array"){
        const auto lo=integer(f(schema,"minItems"));const auto* maximum=schema.find("maxItems");if(lo<0)throw FormError("Invalid array minimum");
        const auto hi=maximum?integer(*maximum):std::int64_t{};if(maximum&&hi<lo)throw FormError("A supported bounded array domain is required");
        if(!maximum||hi>4096){
            // Keep the existing 4096-field collection capacity separate from
            // Source semantics. Large or absent maxima use explicit entry counts.
            if(lo>4096)throw FormError("This form cannot display that many entries");
            p->countInput=std::make_unique<juce::TextEditor>();p->countInput->setComponentID(ju("typed-count-input-"+path));p->countInput->setTextToShowWhenEmpty(ju("Enter your actual number of entries"),juce::Colours::grey);body_.addAndMakeVisible(*p->countInput);
            p->countApply=std::make_unique<juce::TextButton>("Use this entry count");p->countApply->setComponentID(ju("typed-count-apply-"+path));body_.addAndMakeVisible(*p->countApply);
            p->countError=std::make_unique<juce::Label>();p->countError->setComponentID(ju("typed-count-error-"+path));p->countError->setColour(juce::Label::textColourId,juce::Colour(0xff9c2433));body_.addAndMakeVisible(*p->countError);
            auto* field=p.get();const auto serial=p->serial;const auto generation=generation_;juce::Component::SafePointer<TypedManualForm> safe(this);
            p->countInput->onTextChange=[safe,field,generation,path,serial]{if(!safe||generation!=safe->generation_||!safe->current()||!safe->sameField(serial,path))return;field->explicitCountReady=false;field->countError->setText({},juce::dontSendNotification);safe->changed(generation,path,serial);};
            p->countApply->onClick=[safe,field,generation,path,serial,lo,hi,hasMaximum=maximum!=nullptr]{if(!safe||generation!=safe->generation_||!safe->current()||!safe->sameField(serial,path))return;field->explicitCountReady=false;try{const auto raw=field->countInput->getText().toStdString();if(raw.empty()||!std::all_of(raw.begin(),raw.end(),[](char c){return c>='0'&&c<='9';}))throw FormError("Enter a whole number of entries");const auto parsed=json::parse(raw);const auto amount=integer(parsed);if(amount<lo)throw FormError("Too few entries for this task");if(hasMaximum&&amount>hi)throw FormError("Too many entries for this task");if(amount>4096)throw FormError("This form can display at most 4096 entries; this is a display limit, not a printed Source limit");safe->buildArray(*field,static_cast<std::size_t>(amount));field->explicitCountReady=true;field->countError->setText({},juce::dontSendNotification);}catch(const std::exception& e){field->countError->setText(ju(e.what()),juce::dontSendNotification);}safe->resized();safe->changed(generation,path,serial);};
        }else{if(lo==hi)buildArray(*p,static_cast<std::size_t>(lo));else{p->count=std::make_unique<juce::ComboBox>();p->count->setComponentID(ju("typed-count-"+path));p->count->setTextWhenNothingSelected("Choose the number of entries");for(auto n=lo;n<=hi;++n)p->count->addItem(ju(std::to_string(n)),static_cast<int>(n+1));body_.addAndMakeVisible(*p->count);auto* field=p.get();const auto serial=p->serial;const auto generation=generation_;juce::Component::SafePointer<TypedManualForm> safe(this);p->count->onChange=[safe,field,generation,path,serial]{if(!safe||generation!=safe->generation_||!safe->current()||!safe->sameField(serial,path))return;const auto n=field->count->getSelectedId();if(n<1)return;safe->buildArray(*field,static_cast<std::size_t>(n-1));safe->resized();safe->changed(generation,path,serial);};}}
    }
    else if(p->kind=="boolean"){p->ack=std::make_unique<juce::ToggleButton>();checkbox(*p->ack,"typed-field-"+path,"I explicitly report: "+label(schema,name));body_.addAndMakeVisible(*p->ack);}
    else if(p->kind=="string"||p->kind=="integer"||p->kind=="number"){if(p->kind=="number"){const auto* lo=schema.find("minimum");const auto* hi=schema.find("maximum");if(lo)decimal(*lo);if(hi)decimal(*hi);if(lo&&hi&&compareNumbers(*lo,*hi)>0)throw FormError("Numeric minimum exceeds maximum");if(schema.find("nonzero_multiple_of"))throw FormError("Register shift multiples require an integer field");}p->text=std::make_unique<juce::TextEditor>();p->text->setComponentID(ju("typed-field-"+path));p->text->setTextToShowWhenEmpty(ju(p->kind=="string"?"Enter your own response":"Enter your own number"),juce::Colours::grey);body_.addAndMakeVisible(*p->text);if(nullable(schema)){p->unknown=std::make_unique<juce::ToggleButton>();checkbox(*p->unknown,"typed-unknown-"+path,"Unknown / not supplied");body_.addAndMakeVisible(*p->unknown);}}
    else if(p->kind=="null"&&f(schema,"type")==V("null"))p->label->setText(ju(label(schema,name)+" — Not applicable in this source stage."),juce::dontSendNotification);
    else throw FormError("Unsupported learner form schema");wire(*p);return p;
}
void TypedManualForm::buildArray(Field& p,std::size_t count){p.children.clear();for(std::size_t n=0;n<count;++n)p.children.push_back(build(f(p.schema,"items"),p.path+"/"+std::to_string(n),"Entry "+std::to_string(n+1)));}
V TypedManualForm::readField(const Field& p)const{
    if(p.kind=="null")return nullptr;
    if(p.kind=="constant")return f(p.schema,"const");if(p.kind=="enum"){const auto n=p.choice->getSelectedId();if(n<1||static_cast<std::size_t>(n)>p.choices.size())throw FormError("Choose an explicit response");return p.choices[static_cast<std::size_t>(n-1)];}
    if(p.unknown&&p.unknown->getToggleState())return nullptr;
    if(p.kind=="object"){O out;for(const auto& child:p.children)if(!child->include||child->include->getToggleState())out.emplace(child->name,readField(*child));return out;}
    if(p.kind=="array"){if(p.countInput&&!p.explicitCountReady)throw FormError("Choose and apply the entry count explicitly");if(p.count&&p.count->getSelectedId()==0)throw FormError("Choose the array size explicitly");A out;for(const auto& child:p.children)out.push_back(readField(*child));return out;}
    if(p.kind=="boolean")return p.ack->getToggleState();if(p.unknown&&p.unknown->getToggleState())return nullptr;const auto text=p.text->getText();
    if(p.kind=="string"){if(const auto* lo=p.schema.find("minLength"))if(text.length()<integer(*lo))throw FormError("Your response is too short");if(const auto* hi=p.schema.find("maxLength"))if(text.length()>integer(*hi))throw FormError("Your response is too long");if(const auto* nonblank=p.schema.find("nonblank"))if(*nonblank==V(true)&&text.trim().isEmpty())throw FormError("Enter your response or choose Unknown");return text.toStdString();}
    if(p.kind=="number"){const auto value=finiteNumber(text.toStdString());if(const auto* lo=p.schema.find("minimum"))if(compareNumbers(value,*lo)<0)throw FormError("Your number is below the allowed range");if(const auto* hi=p.schema.find("maximum"))if(compareNumbers(value,*hi)>0)throw FormError("Your number is above the allowed range");return value;}
    const auto raw=text.toStdString();if(raw.empty()||!std::all_of(raw.begin()+(raw[0]=='-'?1:0),raw.end(),[](char c){return c>='0'&&c<='9';}))throw FormError("Enter an integer");std::int64_t n{};try{std::size_t end{};n=std::stoll(raw,&end);if(end!=raw.size())throw FormError("Enter an integer");}catch(...){throw FormError("Enter an integer");}
    if(const auto* lo=p.schema.find("minimum"))if(n<integer(*lo))throw FormError("Your number is below the allowed range");if(const auto* hi=p.schema.find("maximum"))if(n>integer(*hi))throw FormError("Your number is above the allowed range");if(const auto* multiple=p.schema.find("nonzero_multiple_of")){const auto m=integer(*multiple);if(m==0||n==0||n%m!=0)throw FormError("Choose the required nonzero register shift");}return V::fromInteger(n);
}
V TypedManualForm::draftField(const Field& p)const{
    A children;for(const auto& c:p.children)children.push_back(draftField(*c));
    return O{{"kind",p.kind},{"include",p.include?V(p.include->getToggleState()):V{}},{"unknown",p.unknown?V(p.unknown->getToggleState()):V{}},{"text",p.text?V(p.text->getText().toStdString()):V{}},{"choice",p.choice?V::fromInteger(p.choice->getSelectedId()):V{}},{"count",p.count?V::fromInteger(p.count->getSelectedId()):V{}},{"count_text",p.countInput?V(p.countInput->getText().toStdString()):V{}},{"count_ready",p.countInput?V(p.explicitCountReady):V{}},{"children",std::move(children)}};
}
V TypedManualForm::captureDraft()const{
    if(!current()||!form_)throw FormError("The native owner action is stale");
    V v=O{{"format","typed-manual-form-draft-v1"},{"schema_sha256",content::sha256(json::stringify(schema_))},{"fields",draftField(*form_)}};
    const auto bytes=json::stringify(v);json::Limits limits;limits.bytes=8*1024*1024;limits.values=100000;limits.depth=64;json::parse(bytes,limits);return v;
}
void TypedManualForm::restoreDraftField(Field& p,const V& v){
    if(!v.isObject()||v.object().size()!=9||f(v,"kind")!=V(p.kind))throw FormError("Draft field shape differs");
    auto toggle=[&](const char* key,std::unique_ptr<juce::ToggleButton>& c){const auto& x=f(v,key);if(c){if(!x.isBool())throw FormError("Draft toggle differs");c->setToggleState(x.boolean(),juce::dontSendNotification);}else if(!x.null())throw FormError("Unexpected draft toggle");};
    toggle("include",p.include);toggle("unknown",p.unknown);
    auto text=[&](const char* key,std::unique_ptr<juce::TextEditor>& c){const auto& x=f(v,key);if(c){if(!x.isString())throw FormError("Draft text differs");c->setText(ju(x.string()),false);}else if(!x.null())throw FormError("Unexpected draft text");};text("text",p.text);text("count_text",p.countInput);
    auto choice=[&](const char* key,std::unique_ptr<juce::ComboBox>& c){const auto& x=f(v,key);if(c){const auto n=integer(x);if(n<0||n>std::numeric_limits<int>::max()||(n&&c->indexOfItemId(static_cast<int>(n))<0))throw FormError("Draft choice outside current domain");c->setSelectedId(static_cast<int>(n),juce::dontSendNotification);}else if(!x.null())throw FormError("Unexpected draft choice");};choice("choice",p.choice);choice("count",p.count);
    const auto& children=f(v,"children").array();if(children.size()>4096)throw FormError("Draft display capacity exceeded");
    if(p.kind=="array"){
        const auto lo=integer(f(p.schema,"minItems"));const auto* maximum=p.schema.find("maxItems");const auto hi=maximum?integer(*maximum):std::int64_t{};
        const auto count=static_cast<std::int64_t>(children.size());
        if(!p.count&&!p.countInput){if(count!=lo||!maximum||lo!=hi)throw FormError("Fixed draft array differs");}
        else if(p.count&&p.count->getSelectedId()!=0){if(count!=p.count->getSelectedId()-1)throw FormError("Draft count differs from children");}
        else if(p.count&&count!=0&&(count<lo||(maximum&&count>hi)))throw FormError("Unselected draft count has invalid prior children");
        if(p.countInput){const auto& ready=f(v,"count_ready");if(!ready.isBool())throw FormError("Draft applied-count flag differs");p.explicitCountReady=ready.boolean();
            if(p.explicitCountReady){const auto raw=p.countInput->getText().toStdString();if(raw.empty()||!std::all_of(raw.begin(),raw.end(),[](char c){return c>='0'&&c<='9';}))throw FormError("Invalid applied draft count");const auto amount=integer(json::parse(raw));if(amount!=count||amount<lo||(maximum&&amount>hi))throw FormError("Applied draft count differs");}
        }
        buildArray(p,children.size());
    }
    if(!p.countInput&&!f(v,"count_ready").null())throw FormError("Unexpected applied-count flag");
    if(children.size()!=p.children.size())throw FormError("Draft child fields differ");
    for(std::size_t i=0;i<children.size();++i)restoreDraftField(*p.children[i],children[i]);
}
bool TypedManualForm::restoreDraft(const V& v){
    if(!current()||!form_)return false;
    try{const auto bytes=json::stringify(v);json::Limits limits;limits.bytes=8*1024*1024;limits.values=100000;limits.depth=64;json::parse(bytes,limits);
        if(!v.isObject()||v.object().size()!=3||f(v,"format")!=V("typed-manual-form-draft-v1")||f(v,"schema_sha256")!=V(content::sha256(json::stringify(schema_))))return false;
        // Build and validate a complete replacement while the old form remains
        // intact. No callbacks or native actions run during restoration.
        auto candidate=build(schema_,"input","Your report");restoreDraftField(*candidate,f(v,"fields"));if(!current())return false;
        form_=std::move(candidate);resized();return true;
    }catch(...){return false;}
}
V TypedManualForm::read()const{if(!current()||!form_)throw FormError("The native owner action is stale");return readField(*form_);}
const TypedManualForm::Field* TypedManualForm::find(const Field& field,const std::string& path)const{if(field.path==path)return &field;for(const auto& child:field.children)if(const auto* found=find(*child,path))return found;return nullptr;}
std::optional<V> TypedManualForm::valueAt(const std::string& path)const{if(!current()||!form_)return std::nullopt;const auto* field=find(*form_,path);if(!field)return std::nullopt;std::string ancestor=path;for(;;){if(const auto* parent=find(*form_,ancestor)){if(parent->include&&!parent->include->getToggleState())return std::nullopt;if(ancestor!=path&&parent->unknown&&parent->unknown->getToggleState())return std::nullopt;}const auto slash=ancestor.find_last_of('/');if(slash==std::string::npos)break;ancestor.resize(slash);}try{return readField(*field);}catch(...){return std::nullopt;}}
int TypedManualForm::layout(Field& p,int y,int width,int indent){
    const int x=std::min(8+indent*12,std::max(8,width-88)),w=std::max(1,width-x-8);
    const auto labelHeight=manual_text::labelHeight(*p.label,w,p.kind=="constant"?42:24);
    p.label->setBounds(x,y,w,labelHeight);y+=labelHeight+4;
    auto toggle=[&](juce::ToggleButton& control){const auto h=manual_text::toggleHeight(control,w);control.setBounds(x,y,w,h);y+=h+4;};
    if(p.include)toggle(*p.include);
    if(p.choice){p.choice->setBounds(x,y,w,30);y+=34;}if(p.count){p.count->setBounds(x,y,w,30);y+=34;}
    if(p.countInput){p.countInput->setBounds(x,y,w,30);y+=34;}if(p.countApply){p.countApply->setBounds(x,y,w,30);y+=34;}
    if(p.countError){const auto h=manual_text::labelHeight(*p.countError,w,44);p.countError->setBounds(x,y,w,h);y+=h+4;}
    if(p.ack)toggle(*p.ack);
    if(p.text){p.text->setBounds(x,y,w,30);y+=34;}
    if(p.unknown)toggle(*p.unknown);
    for(auto& child:p.children)y=layout(*child,y,width,indent+1);return y;
}
void TypedManualForm::setInstructions(const std::vector<std::string>& lines){std::string text;for(const auto& line:lines)text+=line+"\n\n";if(text!=instructionText_){instructionText_=text;manual_text::setReadOnlyText(instructions_,ju(text));++instructionLayouts_;}resized();}
void TypedManualForm::setHistorySummary(const std::vector<std::string>& lines){reports_->setVisible(false);reports_->set({});history_.setTitle("Your reported actions");std::string text;const auto first=lines.size()>12?lines.size()-12:0;for(std::size_t n=first;n<lines.size();++n)text+=preview(lines[n])+"\n";if(!lines.empty())text+="Full typed reports remain retained by the native owner.";if(text!=historyText_){historyText_=text;manual_text::setReadOnlyText(history_,ju(text));++historyLayouts_;}resized();}
void TypedManualForm::setCommittedReportSummary(const std::vector<std::string>& lines){
    std::string text;for(const auto&line:lines)text+=line+"\n";
    const bool changed=text!=reports_->full;reports_->set(std::move(text));reports_->setVisible(!lines.empty());history_.setVisible(false);historyText_.clear();if(changed)++historyLayouts_;resized();
}
void TypedManualForm::resized(){
    auto r=getLocalBounds().reduced(8);instructions_.setVisible(!instructionText_.empty());history_.setVisible(!reports_->isVisible()&&!historyText_.empty());
    // Reserve the paged report before the source instructions. Its navigation
    // consumes30px; dividing an already reduced remainder hid the report text.
    if(reports_->isVisible()){
        const auto height=std::min(r.getHeight(),std::clamp(r.getHeight()/3,80,170));
        reports_->setBounds(r.removeFromBottom(height));r.removeFromBottom(std::min(6,r.getHeight()));
    }
    if(instructions_.isVisible()){instructions_.setBounds(r.removeFromTop(std::min(140,r.getHeight()/3)));r.removeFromTop(std::min(6,r.getHeight()));}
    if(history_.isVisible()){history_.setBounds(r.removeFromBottom(std::min(70,r.getHeight()/4)));r.removeFromBottom(std::min(6,r.getHeight()));}
    viewport_.setBounds(r);const auto width=std::max(120,viewport_.getWidth()-18);const auto height=form_?layout(*form_,4,width):32;body_.setSize(width,std::max(height,viewport_.getHeight()));
}
void TypedManualForm::paint(juce::Graphics& g){g.fillAll(juce::Colour(0xfff6f4ef));}
} // namespace fathom::desktop
