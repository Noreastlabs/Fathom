#pragma once
// ABI consumed by the retained pinned JUCE CoreAudio instrumentation.
extern "C" int fathom_bind_epoch();
extern "C" void fathom_property(int,unsigned,unsigned,unsigned,unsigned,unsigned);
extern "C" void fathom_native_block(int,unsigned,int,const AudioTimeStamp*,const AudioTimeStamp*,const AudioTimeStamp*);
extern "C" void fathom_skip(int,int,int);
extern "C" void fathom_native_output(int,const AudioBufferList*);
extern "C" void fathom_backend_error(int,int,int,const char*);
