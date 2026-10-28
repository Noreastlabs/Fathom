#pragma once
#include <array>
#include <optional>

namespace fathom::desktop {
// Input adapters share this boundary; it owns no transport, clock or result.
enum class PracticeCommand { Connect, Enable, Start, Pause, Resume, ToggleTransport,
    Stop, Clean, Save, Retry, Again, ToggleFocus };

class PracticeShortcutGate final {
public:
    static constexpr std::array<int,7> keys{{32,27,'C','S','R','A','F'}};
    static std::optional<PracticeCommand> command(int key, bool modified=false) noexcept {
        if(modified)return {};
        switch(key){
            case 32:return PracticeCommand::ToggleTransport;
            case 27:return PracticeCommand::Stop;
            case 'C':return PracticeCommand::Clean;
            case 'S':return PracticeCommand::Save;
            case 'R':return PracticeCommand::Retry;
            case 'A':return PracticeCommand::Again;
            case 'F':return PracticeCommand::ToggleFocus;
            default:return {};
        }
    }
    bool press(int key, bool nativeRepeat=false) noexcept {
        if(nativeRepeat)return false;
        for(std::size_t i=0;i<keys.size();++i)if(keys[i]==key){
            if(held_[i])return false;
            held_[i]=true;return true;
        }
        return false;
    }
    void release(int key) noexcept {
        for(std::size_t i=0;i<keys.size();++i)if(keys[i]==key)held_[i]=false;
    }
    void abandonInactiveGestures() noexcept { held_.fill(false); }
private:
    std::array<bool,keys.size()> held_{};
};
} // namespace fathom::desktop
