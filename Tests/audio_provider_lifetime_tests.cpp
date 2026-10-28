#include "desktop/PreparedToolSound.hpp"
#include <thread>
#include <iostream>
#include <chrono>
using namespace fathom;int checks=0;static void ck(bool x,const char*m){++checks;if(!x)throw std::runtime_error(m);}
struct Provider {
 inline static std::atomic<int> destroyed{0},seen{0};inline static std::atomic<bool>entered{false},release{false};int id;
 explicit Provider(int n):id(n){}~Provider(){++destroyed;}
 static void observe(void*p,const output::Snapshot&)noexcept{seen=static_cast<Provider*>(p)->id;}
 static scheduler::BlockOutcome render(void*p,const output::Owner&,std::uint32_t,std::uint32_t,platform::Buses&)noexcept{
  auto*self=static_cast<Provider*>(p);const auto before=self->id;if(before==1){entered=true;const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!release&&std::chrono::steady_clock::now()<end)std::this_thread::yield();}seen=self->id;return{before==self->id,0,false};
 }
};
int main(){try{using Slot=desktop::PreparedToolSound<Provider>;platform::Buses buses{};output::Owner owner{};{
 Slot slot;ck(!slot.current(),"unprepared slot has no provider");slot.publish(std::make_unique<Provider>(1));bool valid=false;std::thread callback([&]{valid=Slot::render(&slot,owner,44100,256,buses).valid;});const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!Provider::entered&&std::chrono::steady_clock::now()<end)std::this_thread::yield();if(!Provider::entered){Provider::release=true;callback.join();throw std::runtime_error("callback barrier");}
 slot.publish(std::make_unique<Provider>(2));const bool held=Provider::destroyed==0;Provider::release=true;callback.join();ck(held&&valid&&Provider::seen==1,"old callback retains original provider across new publication");Slot::observe(&slot,{});ck(Provider::seen==2,"new callbacks observe new prepared provider");for(int i=3;i<=256;++i)slot.publish(std::make_unique<Provider>(i));bool refused=false;try{slot.publish(std::make_unique<Provider>(257));}catch(const std::runtime_error&){refused=true;}ck(refused&&slot.current()->id==256&&Provider::destroyed==1,"bounded refusal preserves current and all prior providers");
 }ck(Provider::destroyed==257,"all retained generations destroyed only after callback joined and slot released");std::cout<<"PASS "<<checks<<" provider lifetime checks; synthetic thread only\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
