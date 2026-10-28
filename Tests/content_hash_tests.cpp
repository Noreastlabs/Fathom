#include "content/Canonical.hpp"
#include <juce_cryptography/juce_cryptography.h>
#include <array>
#include <iostream>
#include <stdexcept>

int main(){
    int checks=0;
    try{
        const auto check=[&](bool ok,const char* label){
            ++checks;if(!ok)throw std::runtime_error(label);
        };
        const auto known=[&](const std::string& bytes,const char* expected){
            check(fathom::content::sha256(bytes)==expected,"Independent fixed SHA256 vector differs");
        };
        known("","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        known("abc","ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
        known("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq","248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");
        known(std::string(1000000,'a'),"cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
        const std::array<std::size_t,18> lengths{0,1,55,56,63,64,65,127,128,129,255,256,257,
            1024*1024-1,1024*1024,1024*1024+1,2*1024*1024,2*1024*1024+17};
        for(const auto size:lengths){
            std::string bytes(size,'\0');
            for(std::size_t i=0;i<size;++i)bytes[i]=static_cast<char>(i%256);
            const auto expected=juce::SHA256(bytes.data(),bytes.size()).toHexString().toStdString();
            const auto actual=fathom::content::sha256(bytes);
            check(actual==expected,"Binary/padding/chunk-boundary digest differs from retained JUCE path");
            check(actual.size()==64&&actual.find_first_not_of("0123456789abcdef")==std::string::npos,
                  "SHA256 output format differs");
        }
        const std::string original{"a\0b",3};
        const auto digest=fathom::content::sha256(original);
        check(digest!=fathom::content::sha256(std::string{"a\0c",3}),"Changed bytes retain a stale digest");
        check(digest==fathom::content::sha256(original),"Prior input does not recover its exact digest");
        check(fathom::content::sha256("ab")!=digest,"Embedded NUL was truncated");
        std::cout<<"PASS "<<checks<<" SHA256 fixed-vector and binary/chunk/identity checks; no GUI/profile\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
