#pragma once
#include <algorithm>
#include <string>
#include <string_view>

namespace fathom::desktop {
// Bound display work by input bytes, preserve valid UTF-8 code points, escape
// control/invalid bytes. The original Reply is never modified or truncated.
inline std::string diagnosticField(std::string_view input,std::size_t limit){
    std::string out;const auto end=std::min(input.size(),limit);std::size_t p=0;
    const char* hex="0123456789ABCDEF";
    const auto escape=[&](unsigned char c){out+="\\x";out+=hex[c>>4];out+=hex[c&15];};
    while(p<end){
        const auto b=static_cast<unsigned char>(input[p]);
        if(b<0x80){if(b<0x20||b==0x7f)escape(b);else out+=static_cast<char>(b);++p;continue;}
        std::size_t n=b>=0xc2&&b<=0xdf?2:b>=0xe0&&b<=0xef?3:b>=0xf0&&b<=0xf4?4:0;
        if(n && p+n>end && p+n<=input.size())break; // never split a valid terminal point
        bool valid=n && p+n<=end;unsigned cp=n?b&((1u<<(7-n))-1):0;
        for(std::size_t j=1;valid&&j<n;++j){auto c=static_cast<unsigned char>(input[p+j]);valid=(c&0xc0)==0x80;cp=(cp<<6)|(c&0x3f);}
        valid=valid&&!(n==3&&cp<0x800)&&!(n==4&&cp<0x10000)&&cp<=0x10ffff&&!(cp>=0xd800&&cp<=0xdfff);
        if(!valid){escape(b);++p;continue;}
        const bool control=(cp>=0x80&&cp<=0x9f)||cp==0x200e||cp==0x200f||(cp>=0x202a&&cp<=0x202e)||(cp>=0x2066&&cp<=0x2069);
        if(control)for(std::size_t j=0;j<n;++j)escape(static_cast<unsigned char>(input[p+j]));
        else out.append(input.substr(p,n));p+=n;
    }
    if(p<input.size())out+=" [display truncated]";
    return out.empty()?"(none)":out;
}
}
