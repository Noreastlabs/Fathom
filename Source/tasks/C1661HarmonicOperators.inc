// Source-bound chosen support; chord identity is musical pitch-set identity.
bool actualSupportingBody(const V& value,const Harmony& h,const Contact& top,bool permitPrintedOutsideTop){
 bool good=true;const auto body=knownActualContacts(value,good);if(!good)return false;
 need(!body.empty()&&body.size()<=5,"C1661_ACTUAL_SUPPORT_BODY_EXTENT");std::set<std::string> strings;std::set<int> tones;
 if(h.body.count(top.midi%12))tones.insert(top.midi%12);else if(!permitPrintedOutsideTop)good=false;
 for(const auto& x:body){good=good&&x.midi<top.midi&&x.string!=top.string&&strings.insert(x.string).second&&h.body.count(x.midi%12);tones.insert(x.midi%12);}
 for(int q:h.quality)good=good&&tones.count(q);return good;
}
bool actualThreeSupportingHarmonies(const V& p,const V& c){
 need(f(c,"schema_version")==V("fathom-private-manual-task-contract.1"),"C1661_FIXED_TOP_SOURCE_SCHEMA");const auto top=contact(f(p,"actual_chosen_fixed_top_contact"));if(!top)return false;
 bool good=top->midi%12==pc(field(c,"Top note"));const auto& choices=f(p,"actual_supporting_harmony_choices").array();need(choices.size()>=3&&choices.size()<=256,"C1661_SOURCE_AT_LEAST_THREE_SUPPORTS");std::set<std::pair<int,std::set<int>>> harmoniesSeen;
 for(const auto& row:choices){need(row.isObject()&&row.object().size()==2,"C1661_CLOSED_ACTUAL_SUPPORT_CHOICE");const auto& symbol=f(row,"actual_chosen_harmony_symbol");if(symbol.null()){good=false;continue;}const auto h=chord(text(symbol));good=actualSupportingBody(f(row,"actual_chosen_harmony_body"),h,*top,false)&&good;harmoniesSeen.insert({namedChord(text(symbol)).root,h.body});}
 return good&&harmoniesSeen.size()>=3;
}
bool actualPrintedConnectorTop(const V& p,const V& c){
 need(f(c,"schema_version")==V("fathom-private-manual-task-contract.1"),"C1661_CONNECTOR_SOURCE_SCHEMA");const auto names=harmonies(field(c,"Progression"));need(names.size()==3,"C1661_THREE_PRINTED_CONNECTOR_HARMONIES");const auto top=contact(f(p,"actual_chosen_source_top_contact"));if(!top)return false;
 bool good=top->midi%12==pc(field(c,"Top"));const auto& function=field(c,"Function");std::set<int> destinations;
 if(function=="C# is 3 of A7; resolve into Dm7")destinations=chord(names.back()).body;
 else if(function=="F# is 3 of D7; resolve toward G")destinations={pc("G")};
 else if(function=="D# is 3 of B7; resolve to E/G")destinations={pc("E"),pc("G")};
 else need(function=="common/connector tone"||function=="passing diminished function"||function=="chromatic bass connector","C1661_CLOSED_PRINTED_CONNECTOR_FUNCTION");
 const auto resolution=contact(f(p,"actual_chosen_final_resolved_top_contact"));if(destinations.empty())good=good&&f(p,"actual_chosen_final_resolved_top_contact").null();else if(!resolution)good=false;else good=good&&destinations.count(resolution->midi%12);
 const auto& body=f(p,"actual_chosen_three_source_harmony_bodies").array();need(body.size()==3,"C1661_WHOLE_CONNECTOR_BODY_EXTENT");
 for(std::size_t i=0;i<3;++i){const auto& current=(i==2&&resolution)?*resolution:*top;good=actualSupportingBody(body[i],chord(names[i]),current,true)&&good;}return good;
}
