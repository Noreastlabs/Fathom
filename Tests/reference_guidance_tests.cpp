#include "desktop/ReferenceGuidance.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;using namespace fathom::desktop;
int main(int argc,char** argv){int n=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("New output required");std::filesystem::create_directories(argv[1]);const std::filesystem::path dir=argv[1];std::ofstream log(dir/"checks.tsv"),trace(dir/"guidance.tsv");
 const auto ck=[&](bool b,const std::string& s){++n;log<<s<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(s);};using S=output::State;
 ReferenceGuidanceInput i;
 const auto read=[&](const std::string& id){const auto g=referenceGuidance(i);trace<<id<<'\t'<<g.state<<'\t'<<g.next<<'\n';ck(!g.state.empty()&&!g.next.empty()&&g.state.find('\n')==std::string::npos&&g.next.find('\n')==std::string::npos,id+" two explicit lines");ck(g.state.size()<80&&g.next.size()<90,id+" finite copy");return g;};
 for(auto s:{S::Closed,S::Awaiting,S::Observed,S::Ready,S::Running,S::Paused,S::Unresolved,S::Fault}){i.output.state=s;read("state-"+std::to_string(static_cast<int>(s)));}
 for(auto s:{S::Unresolved,S::Fault}){
  i={};i.output.state=s;i.output.ownsOutcome=true;i.output.pendingOutcome=true;i.started=true;i.ownerMatches=true;i.canDone=true;i.output.owner.id[0]=42;i.output.owner.epoch=12;i.output.owner.generation=3;
  const auto g=read("failed-Done-"+std::to_string(static_cast<int>(s)));const std::string old="Output command could not be queued. Stop and reconnect.";
  ck(g.next.find("Choose Finish tone")!=std::string::npos&&g.next.find("reconnect")==std::string::npos&&g.next.find("Stop")==std::string::npos,"pending original offers Done not disabled Stop/Connect");
  ck(!i.canConnect&&!i.canStop&&old.find("Stop and reconnect")!=std::string::npos,"old priority counterexample source-mapped only; no real queue failure");
  const auto d=referenceDiagnostics(i,old,"synthetic backend old error");ck(d.find(old)!=std::string::npos&&g.primary().find(old)==std::string::npos,"raw old message remains only diagnostic");
  i.resolving=true;i.canDone=false;ck(read("resolving").state.find("Acknowledging")!=std::string::npos&&referenceGuidance(i).next.find("Wait")!=std::string::npos,"queued resolution waits without repeat Done");
  i.resolving=false;i.ownerMatches=false;i.canDone=true;ck(read("mismatch").next.find("cannot be acknowledged here")!=std::string::npos,"owner match guards otherwise enabled Done");
  i.ownerMatches=true;i.canDone=false;ck(read("Done-unavailable").next.find("Choose Finish tone")==std::string::npos,"no unavailable Done instruction");
 }
 i={};i.output.state=S::Ready;i.started=true;i.stopWhenRunning=true;ck(read("stop-before-running").state.find("stop has been requested")!=std::string::npos,"requested stop distinct before running");i.stopWhenRunning=false;ck(read("start-requested").state.find("start has been requested")!=std::string::npos&&referenceGuidance(i).next.find("do not start")!=std::string::npos,"queued start not playing or another Play");
 i.output.state=S::Closed;ck(read("cancelled-start-closing").next.find("do not reconnect")!=std::string::npos,"cancelled start closing awaits cleanup");i.started=false;i.canConnect=true;i.output.stopRequested=true;ck(read("closed").next.find("Open Audio settings")!=std::string::npos,"unowned Closed routes shared Audio settings");
 i={};i.output.state=S::Observed;ck(read("enable-unavailable").next.find("Choose Enable")==std::string::npos,"unavailable Enable withheld");i.canEnable=true;ck(read("observed").next.find("Audio settings to enable")!=std::string::npos,"observed explicit enable");
 i={};i.output.state=S::Ready;i.canPlay=true;ck(read("ready").next.find("Play tone explicitly")!=std::string::npos,"ready requires explicit Play");i.canPlay=false;ck(read("play-unavailable").next.find("Choose Play")==std::string::npos,"unavailable Play withheld");
 i={};i.output.state=S::Running;i.output.ownsOutcome=true;i.canStop=true;ck(read("running").next.find("Use Stop")!=std::string::npos,"running explicit stop");i.output.stopRequested=true;ck(read("requested-stop").state.find("stop has been requested")!=std::string::npos,"requested stop not confirmed silence");
 i={};i.output.state=S::Fault;i.output.stopRequested=true;i.canBack=true;ck(read("unowned-backend-fault").next.find("Back to leave")!=std::string::npos,"unowned fault Back then settings");i.canBack=false;ck(read("back-unavailable").next.find("Choose Back")==std::string::npos,"unavailable Back withheld");
 i.output.owner.id[0]=42;i.output.owner.epoch=12;i.output.owner.generation=3;const auto original=i;const auto once=referenceGuidance(i).primary();const auto twice=referenceGuidance(i).primary();ck(once==twice&&i.output.owner==original.output.owner&&i.output.pendingOutcome==original.output.pendingOutcome&&i.output.state==original.output.state,"duplicate projection preserves input and owner");
 std::string raw="é ♯\n";raw.push_back('\0');raw.push_back(static_cast<char>(0xff));const auto before=raw;const auto d=referenceDiagnostics(i,raw,std::string(2000,'x'));ck(raw==before&&d.find("é ♯")!=std::string::npos&&d.find("\\x00")!=std::string::npos&&d.find("\\xFF")!=std::string::npos,"Unicode and unsafe bytes visible without input mutation");ck(d.find("[display truncated]")!=std::string::npos&&d.find("Owner epoch / generation: 12 / 3")!=std::string::npos,"per-field bound and exact owner context");ck(d.find("2a000000000000000000000000000000")!=std::string::npos,"original owner exact hex");
 ck(diagnosticField("A♯Z",3)=="A [display truncated]"&&diagnosticField("\xe2\x80\xae",8)=="\\xE2\\x80\\xAE","multibyte truncation and bidi safely retained");
 std::ofstream(dir/"details.txt")<<d;log.flush();trace.flush();ck(log.good()&&trace.good(),"evidence flush");std::cout<<"PASS "<<n<<" synthetic reference guidance checks; no output connection\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<n<<": "<<e.what()<<'\n';return 1;}}
