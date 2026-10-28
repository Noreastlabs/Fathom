// Standalone compatibility link shim only. App uses content::Canonical.
#include "content/Canonical.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <iomanip>
#include <sstream>
namespace fathom::content {
std::string sha256(const std::string& raw){std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> bytes{};CC_SHA256(raw.data(),static_cast<CC_LONG>(raw.size()),bytes.data());std::ostringstream out;for(auto b:bytes)out<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(b);return out.str();}
}
