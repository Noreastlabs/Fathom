#include "desktop/PracticeCommands.hpp"
#include <iostream>
#include <stdexcept>
using namespace fathom::desktop;
int main(){int n=0;try{
 const auto ck=[&](bool okay,const char* text){++n;if(!okay)throw std::runtime_error(text);};
 const std::array<PracticeCommand,7> expected{{PracticeCommand::ToggleTransport,PracticeCommand::Stop,PracticeCommand::Clean,PracticeCommand::Save,PracticeCommand::Retry,PracticeCommand::Again,PracticeCommand::ToggleFocus}};
 PracticeShortcutGate gate;
 for(std::size_t i=0;i<expected.size();++i){const int key=PracticeShortcutGate::keys[i];
  ck(PracticeShortcutGate::command(key)==expected[i],"declared mnemonic");ck(!PracticeShortcutGate::command(key,true),"modified text/OS preserved");
  ck(!gate.press(key,true),"orphan native repeat never invokes");ck(gate.press(key),"initial press");ck(!gate.press(key),"duplicate down");ck(!gate.press(key,true),"held repeat");
  gate.abandonInactiveGestures();ck(!gate.press(key,true),"repeat after inactive clearing");ck(gate.press(key),"fresh gesture after return");
  gate.release(999);ck(!gate.press(key),"unrelated release does not arm");gate.release(key);ck(gate.press(key),"exact release rearms");gate.release(key);
 }
 for(int key:{0,9,13,65+32,0x2192,999})ck(!PracticeShortcutGate::command(key),"unmapped keys preserved");
 ck(gate.press(32),"Space first gesture");ck(gate.press(27),"Stop independent of held Space");gate.release(27);ck(!gate.press(32,true),"Stop release cannot restart held Space");
 std::cout<<"PASS "<<n<<" requirement-derived command/gesture checks; no audio or human input\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<n<<": "<<e.what()<<'\n';return 1;}}
