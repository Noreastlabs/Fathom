// Exact eighteen-only declarations. Existing contact/chord/pitch helpers are
// reused; no new musical model, clock, observation, source role or owner.
bool c18Visible(const V& v){if(v.null())return false;need(v.isString(),"C18_DECLARED_TEXT_TYPE");return declared_manual_text::visibleUtf8(v.string())&&utf8TextLength(v.string())<=4096;}
bool c18Integer(const V& v,std::int64_t& n,std::int64_t lo,std::int64_t hi){if(v.null())return false;need(v.integer(n)&&lo<=n&&n<=hi,"C18_DECLARED_INTEGER_DOMAIN");return true;}
bool c18Yes(const V& v){if(v.null())return false;need(v.isBool(),"C18_REPORTED_BOOLEAN_TYPE");return v==V(true);}
bool c18Source(const V& d,const V& c,std::string& policy){const auto key=text(f(d,"source_key"));const auto* a=manual_procedure_graph_c18_authority::find(key);need(a,"C18_EXACT_SOURCE_KEY");need(c==json::parse(a->contract),"C18_EXACT_ORIGINAL_CONTRACT");policy=a->policy;return true;}
struct C18Event {int arrival{};Contact start;std::string technique;const V* raw{};};
std::optional<C18Event> c18Event(const V& e){need(e.isObject()&&e.object().size()==10,"C18_CLOSED_ACTUAL_EVENT");auto start=contact(f(e,"start_contact"));const auto& motion=f(e,"technique");std::int64_t arrival{};if(!start||motion.null()||!c18Integer(f(e,"arrival_midi"),arrival,40,112))return std::nullopt;const auto t=text(motion);static const std::set<std::string> allowed{"plain","sustain","bend","pre-bend","slide","finger","harmonic","vibrato","rake"};need(allowed.count(t),"C18_ACTUAL_TECHNIQUE_DOMAIN");bool good=true;
 if(t=="bend"||t=="pre-bend")good=arrival>start->midi;
 else if(t=="slide"){auto last=contact(f(e,"arrival_contact"));good=last&&last->string==start->string&&last->fret!=start->fret&&last->midi==arrival;}
 else if(t=="harmonic")good=c18Visible(f(e,"actual_harmonic_reference"));
 else good=arrival==start->midi;
 if(t=="rake"){const auto& muted=f(e,"actual_rake_muted_strings");if(muted.null())return std::nullopt;need(muted.isArray()&&!muted.array().empty()&&muted.array().size()<=5,"C18_ACTUAL_RAKE_PREFIX_EXTENT");std::set<std::string> unique;for(const auto& m:muted.array()){need(m.isObject()&&m.object().size()==2,"C18_CLOSED_MUTED_STRING_REPORT");const auto& string=f(m,"string");if(string.null()){good=false;continue;}const auto s=text(string);need(std::string("EADGBe").find(s)!=std::string::npos&&s.size()==1,"C18_RAKE_STRING_DOMAIN");good=good&&s!=start->string&&unique.insert(s).second&&c18Yes(f(m,"reported_muted"));}good=good&&c18Yes(f(e,"picked_attack_reported"));}
 if(!good)return std::nullopt;return C18Event{static_cast<int>(arrival),*start,t,&e};
}
std::vector<Contact> c18Motif(const V& m,bool& good){if(m.null()){good=false;return {};}need(m.isArray()&&(m.array().size()==3||m.array().size()==4),"C18_SOURCE_THREE_OR_FOUR_NOTE_MOTIF");std::vector<Contact> out;for(const auto& v:m.array()){auto x=contact(v);if(x)out.push_back(*x);else good=false;}return out;}
bool c18Setup(const V& p,const std::string& policy){std::int64_t units{};bool good=c18Visible(f(p,"actual_pulse_choice"))&&c18Integer(f(p,"actual_units_per_bar"),units,1,256);
 if(policy.rfind("station_",0)==0||policy=="expression_arc"){
  const auto& names=f(p,"actual_harmonies");if(names.null())return false;need(names.isArray()&&names.array().size()==8,"C18_SELECTED_COMPLETE_EIGHT_BAR_HARMONY");for(const auto& n:names.array()){if(n.null()){good=false;continue;}(void)chord(text(n));}
  good=good&&c18Visible(f(p,"actual_form_reference"));
 }
 if(policy=="station_2"||policy=="station_7"){(void)c18Motif(f(p,"actual_motif"),good);good=good&&c18Visible(f(p,"actual_previous_form_and_motif_reference"));}
 if(policy=="station_3"){const auto& prev=f(p,"actual_previous_chord");if(prev.null())good=false;else (void)chord(text(prev));}
 if(policy=="station_4")good=good&&c18Visible(f(p,"actual_displacement_plan"));
 if(policy=="station_5"||policy=="expression_arc"||policy=="command_Climax")good=good&&c18Visible(f(p,"actual_climax_and_release_plan"));
 if(policy=="station_7")good=good&&c18Visible(f(p,"actual_contrast_plan"));
 if(policy=="station_8")good=good&&c18Visible(f(p,"actual_phrase_cadence_plan"));
 return good;
}
bool c18Whole(const V& p,const V& c,const V::Object& saved,const std::string& policy){(void)c;auto it=saved.find("setup");need(it!=saved.end(),"C18_OWNED_SETUP_REQUIRED");const auto& setup=it->second;std::int64_t units{};if(!c18Integer(f(setup,"actual_units_per_bar"),units,1,256))return false;
 const bool command=policy.rfind("command_",0)==0;const auto& bars=f(p,"actual_bars");need(bars.isArray()&&bars.array().size()==(command?1:8),"C18_COMPLETE_SOURCE_BAR_EXTENT");bool good=c18Visible(f(p,"actual_full_source_comparison"));std::vector<std::vector<C18Event>> events;std::vector<std::int64_t> rests,levels;std::vector<std::string> focuses;
 for(const auto& b:bars.array()){
  need(b.isObject()&&b.object().size()==6,"C18_CLOSED_COMPLETE_BAR");good=good&&c18Yes(f(b,"whole_actual_bar_reported"))&&c18Visible(f(b,"actual_choice_description"));std::int64_t rest{};if(!c18Integer(f(b,"rest_units"),rest,0,units)){good=false;rest=-1;}rests.push_back(rest);
  const auto& a=f(b,"events");need(a.isArray()&&a.array().size()<=128,"C18_FINITE_ACTUAL_BAR_EVENT_COLLECTION");std::vector<C18Event> parsed;for(const auto& e:a.array()){auto value=c18Event(e);if(value)parsed.push_back(*value);else good=false;}good=good&&(rest==units?a.array().empty():!a.array().empty());events.push_back(parsed);
  std::int64_t level=-1;if(policy=="expression_arc"&&!c18Integer(f(b,"actual_intensity"),level,1,4))good=false;levels.push_back(level);focuses.push_back(f(b,"actual_focus").null()?"":text(f(b,"actual_focus")));
 }
 if(!good)return false;
 if(policy=="fixed_targets"){
  static const std::array<int,8> targets{{5,11,4,11,5,8,0,9}};
  for(std::size_t i=0;i<8;++i){good=good&&std::any_of(events[i].begin(),events[i].end(),[&](const C18Event& e){return e.arrival%12==targets[i];});}
  good=good&&std::any_of(events[2].begin(),events[2].end(),[](const C18Event& e){return e.technique=="sustain"||e.technique=="vibrato";});
  good=good&&(rests[3]>0||std::any_of(events[3].begin(),events[3].end(),[](const C18Event& e){return e.technique!="plain"&&e.technique!="sustain";}));
  good=good&&std::any_of(events[5].begin(),events[5].end(),[](const C18Event& e){return (e.technique=="bend"||e.technique=="pre-bend")&&e.arrival%12==8;});
 }
 if(command){
  const auto cmd=policy.substr(8);std::size_t bends=0,slides=0,harmonics=0;for(const auto& e:events[0]){bends+=e.technique=="bend"||e.technique=="pre-bend";slides+=e.technique=="slide";harmonics+=e.technique=="harmonic";}
  if(cmd=="Plain")for(const auto& e:events[0])good=good&&(e.technique=="plain"||e.technique=="sustain");
  else if(cmd=="Bend")good=good&&bends==1;
  else if(cmd=="Slide")good=good&&slides==1;
  else if(cmd=="Finger")for(const auto& e:events[0]){const auto& picked=f(*e.raw,"picked_attack_reported");if(picked.null())good=false;else{need(picked.isBool(),"C18_ACTUAL_PICK_REPORT_TYPE");good=good&&picked==V(false);}}
  else if(cmd=="Space")good=good&&rests[0]>=0&&rests[0]*2>=units;
  else if(cmd=="Harmonic")good=good&&harmonics==1;
  else if(cmd=="Soft")for(const auto& e:events[0]){const auto& dyn=f(*e.raw,"actual_dynamic");good=good&&!dyn.null()&&(dyn==V("pp")||dyn==V("p")||dyn==V("mp"));}
  else {need(cmd=="Climax","C18_LITERAL_COMMAND");std::size_t count=0;for(std::size_t i=0;i<events[0].size();++i){std::int64_t intensity{};if(!c18Integer(f(*events[0][i].raw,"intensity"),intensity,1,4)){good=false;continue;}if(intensity!=4)continue;++count;if(i+1<events[0].size()){std::int64_t next{};good=good&&c18Integer(f(*events[0][i+1].raw,"intensity"),next,1,4)&&next<4;}else good=good&&rests[0]>0;}good=good&&count==1&&c18Yes(f(p,"actual_immediate_release_reported"));}
 }
 if(policy=="station_1"){const auto& names=f(setup,"actual_harmonies").array();for(std::size_t i=0;i<8;++i){const auto h=chord(text(names[i]));for(const auto& e:events[i])good=good&&h.body.count(e.arrival%12);}}
 if(policy=="station_2"){bool known=true;(void)c18Motif(f(setup,"actual_motif"),known);const auto& each=f(p,"actual_motif_developed_in_each_bar");if(each.null())return false;need(each.isArray()&&each.array().size()==8,"C18_FULL_MOTIF_DEVELOPMENT_FORM");for(const auto& v:each.array())good=good&&c18Yes(v);good=good&&known;}
 if(policy=="station_3"){
  const auto& names=f(setup,"actual_harmonies").array();std::string previous=text(f(setup,"actual_previous_chord"));std::vector<std::string> changed;for(const auto& n:names){const auto name=text(n);if(name!=previous)changed.push_back(name);previous=name;}
  const auto& heard=f(p,"actual_targets_sung_before_changes");if(heard.null())return false;need(heard.isArray()&&heard.array().size()==changed.size(),"C18_EACH_ACTUAL_CHORD_CHANGE_TARGET");for(std::size_t i=0;i<changed.size();++i){const auto& t=heard.array()[i];need(t.isObject()&&t.object().size()==3,"C18_CLOSED_TARGET_REPORT");std::int64_t target{};good=good&&c18Integer(f(t,"target_midi"),target,40,112)&&chord(changed[i]).body.count(static_cast<int>(target)%12)&&c18Yes(f(t,"preheard_and_sung_reported"))&&c18Yes(f(t,"before_that_change_reported"));}
  good=good&&!changed.empty();
 }
 if(policy=="station_4"){std::int64_t count{};good=good&&c18Integer(f(p,"actual_displacement_occurrences"),count,0,128)&&count==1&&c18Yes(f(p,"planned_displacement_applied_reported"));}
 if(policy=="station_5"){
  const auto& x=f(p,"actual_climax_position");if(x.null())return false;need(x.isObject()&&x.object().size()==2,"C18_ONE_CHOSEN_CLIMAX_POSITION");std::int64_t bar{},event{};good=good&&c18Integer(f(x,"bar"),bar,0,7)&&c18Integer(f(x,"event"),event,0,127);if(!good)return false;need(static_cast<std::size_t>(event)<events[bar].size(),"C18_CLIMAX_ACTUAL_EVENT_EXISTS");const auto& v=events[bar][event];good=good&&(v.technique=="bend"||v.technique=="pre-bend"||v.technique=="vibrato")&&c18Yes(f(p,"planned_bend_vibrato_climax_reported"));
 }
 if(policy=="station_6")good=good&&std::count(rests.begin(),rests.end(),units)==1&&c18Yes(f(p,"entire_silent_bar_reported"));
 if(policy=="station_7"){
  bool known=true;const auto motif=c18Motif(f(setup,"actual_motif"),known);std::int64_t contrastBar{};good=good&&known&&c18Integer(f(p,"actual_contrast_end_bar"),contrastBar,0,6)&&c18Yes(f(p,"contrast_then_original_return_reported"));if(!good)return false;
  std::vector<int> later;for(std::size_t i=static_cast<std::size_t>(contrastBar+1);i<8;++i)for(const auto& e:events[i])later.push_back(e.arrival);std::vector<int> original;for(const auto& e:motif)original.push_back(e.midi);good=good&&std::search(later.begin(),later.end(),original.begin(),original.end())!=later.end();
 }
 if(policy=="station_8"){
  const auto h=chord(text(f(setup,"actual_harmonies").array().back()));good=good&&!events.back().empty()&&h.body.count(events.back().back().arrival%12)&&c18Yes(f(p,"clear_phrase_cadence_reported"));
 }
 if(policy=="expression_arc"){
  static const std::array<std::pair<int,int>,8> ranges{{{1,2},{1,2},{2,3},{2,3},{3,4},{3,4},{2,2},{1,1}}};
  for(std::size_t i=0;i<8;++i){good=good&&ranges[i].first<=levels[i]&&levels[i]<=ranges[i].second;if(i<2)good=good&&(focuses[i]=="plain notes"||focuses[i]=="slides"||focuses[i]=="narrow vibrato");else if(i<4)good=good&&(focuses[i]=="rakes"||focuses[i]=="pre-bends"||focuses[i]=="register lift");else if(i<6)good=good&&focuses[i]=="climax region";else if(i==6)good=good&&focuses[i]=="decompression";else good=good&&(focuses[i]=="plain resolution"||focuses[i]=="rest");}
  for(std::size_t i=0;i<4;++i){bool selected=focuses[i]=="register lift";int previous=-1,current=-1;for(const auto& e:events[i]){if(i<2)good=good&&(e.technique=="plain"||e.technique=="sustain"||e.technique=="slide"||(e.technique=="vibrato"&&f(*e.raw,"actual_vibrato_width")==V("narrow")));else good=good&&(e.technique=="plain"||e.technique=="sustain"||e.technique=="rake"||e.technique=="pre-bend");if(focuses[i]=="plain notes")good=good&&(e.technique=="plain"||e.technique=="sustain");if(focuses[i]=="slides")selected=selected||e.technique=="slide";if(focuses[i]=="narrow vibrato")selected=selected||(e.technique=="vibrato"&&f(*e.raw,"actual_vibrato_width")==V("narrow"));if(focuses[i]=="rakes")selected=selected||e.technique=="rake";if(focuses[i]=="pre-bends")selected=selected||e.technique=="pre-bend";current=std::max(current,e.arrival);}if(focuses[i]=="register lift"){for(const auto& e:events[i-1])previous=std::max(previous,e.arrival);selected=previous>=0&&current>previous;}if(focuses[i]!="plain notes")good=good&&selected;}
  const auto& x=f(p,"actual_climax_position");if(x.null())return false;std::int64_t bar{},event{};need(x.isObject()&&x.object().size()==2,"C18_ONE_ARC_CLIMAX");good=good&&c18Integer(f(x,"bar"),bar,4,5)&&c18Integer(f(x,"event"),event,0,127);if(!good)return false;need(static_cast<std::size_t>(event)<events[bar].size(),"C18_ARC_CLIMAX_EXISTS");good=good&&c18Yes(f(p,"one_real_climax_reported"))&&c18Yes(f(p,"decompression_performed_reported"));
  if(focuses[7]=="rest")good=good&&rests[7]==units&&events[7].empty();else good=good&&!events[7].empty()&&events[7].back().technique=="plain"&&c18Yes(f(p,"plain_final_resolution_reported"));
 }
 return good;
}
std::optional<bool> c18ImprovisationGuard(const V& d,const V& p,const V& c,const V::Object& saved){const auto kind=text(f(d,"kind"));if(kind!="c18_improvisation_material")return std::nullopt;need(d.isObject()&&d.object().size()==3,"C18_CLOSED_OPERATOR_DESCRIPTOR");std::string policy;c18Source(d,c,policy);const auto stage=text(f(d,"stage"));if(stage=="setup")return c18Setup(p,policy);need(stage=="whole","C18_CLOSED_COMPLETE_OPERATOR_STAGE");return c18Whole(p,c,saved,policy);}
