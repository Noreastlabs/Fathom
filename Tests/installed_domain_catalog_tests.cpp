#include "progression/InstalledDomainCatalog.hpp"
#include "content/Canonical.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>

using namespace fathom;
using namespace fathom::progression;
namespace {
int checks = 0;
void check(bool value, const char* reason) {
    ++checks;
    if (!value) throw std::runtime_error(reason);
}
template<class F> void refuses(F&& action, const char* reason) {
    bool rejected = false;
    try { action(); } catch (const std::exception&) { rejected = true; }
    check(rejected, reason);
}
json::Value read(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("Missing bounded test fixture");
    return json::parse(std::string(std::istreambuf_iterator<char>(input), {}));
}
storage::Reply confirmed(storage::ProfileStore::Future future) {
    auto reply = future.get();
    if (reply.status != storage::Status::Confirmed)
        throw std::runtime_error("Disposable Store refused: " + reply.code + " " + reply.message);
    return reply;
}
json::Value::Array array(const std::vector<std::string>& values) {
    json::Value::Array result;
    for (const auto& value : values) result.emplace_back(value);
    return result;
}
void save(storage::ProfileStore& store, json::Value value, const std::string& kind,
          const std::string& stamp) {
    auto& context = value.object().at("context");
    if (kind == "Attempt") {
        const auto session = confirmed(store.createSession("session/" + stamp,
            stamp, "UTC"));
        context.object()["session_id"] = session.data.object().at("session_id");
    }
    auto& practice = value.object().at("practice");
    practice.object()["practice_utc"] = stamp;
    practice.object()["local_day"] = stamp.substr(0, 10);
    practice.object()["timezone"] = "UTC";
    value.object().at("result").object()["configuration"] = context.object().at("configuration");
    const auto allocation = confirmed(store.allocate("allocate/" + stamp, kind, context, stamp));
    const auto owner = allocation.data.object().at("owner").string();
    value.object()["owner"] = owner;
    value.object().at("result").object()["key"] = owner;
    const auto bytes = storage::canonical(value);
    confirmed(store.seal("seal/" + stamp, owner, bytes));
    confirmed(store.commit("commit/" + stamp, owner, bytes));
}
json::Value preparedAttempt(json::Value value, const DomainBinding& binding,
                            const lesson::Catalog& installed) {
    const auto identity = installed.admit(binding.item, binding.variant)->identity();
    auto& context = value.object().at("context").object();
    context["item_id"] = binding.item;
    context["variant_id"] = binding.variant;
    context["content_revision"] = json::Value::fromInteger(binding.contentRevision);
    context["content_version"] = binding.contentVersion;
    context["source_manifest_sha256"] = binding.sourceManifestSha256;
    context["source_refs"] = array(binding.sourceRefs);
    context.at("configuration").object()["canonical_variant_id"] = binding.variant;
    auto& content = value.object().at("result").object().at("content").object();
    content["id"] = binding.item;
    content["content_revision"] = json::Value::fromInteger(binding.contentRevision);
    content["content_version"] = binding.contentVersion;
    content["source_manifest_sha256"] = binding.sourceManifestSha256;
    content["source_refs"] = array(binding.sourceRefs);
    content["source_hashes"] = identity.object().at("source_hashes");
    content["legacy_level"] = installed.lesson(binding.item).level;
    return value;
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4 && argc != 5) throw std::runtime_error("Expected installed resources, fixture directory, new Store directory, optional installed proof profile");
        const std::filesystem::path resources = argv[1], fixtures = argv[2], scratch = argv[3];
        check(scratch.is_absolute() && !std::filesystem::exists(scratch), "fresh absolute disposable Store path");
        std::filesystem::create_directories(scratch);
        std::filesystem::permissions(scratch, std::filesystem::perms::owner_all,
                                     std::filesystem::perm_options::replace);
        const auto installed = lesson::Catalog::loadInstalled(resources / "representative-controls",
            {resources / "rung02-extension", resources / "rung03-extension",
             resources / "rung04-extension", resources / "level006-extension",
             resources / "rung05-extension", resources / "level008-extension", resources / "level010-extension",
             resources / "level007-extension", resources / "level009-extension", resources / "level011-extension",
             resources / "level013-extension", resources / "level014-extension", resources / "level015-extension",
             resources / "level016-extension", resources / "level017-extension", resources / "level018-extension",
             resources / "level019-extension", resources / "level020-extension", resources / "level021-extension",
             resources / "level022-extension", resources / "level023-extension", resources / "level024-extension", resources / "level030-extension", resources / "level029-extension", resources / "level025-extension", resources / "level026-extension"});
        const auto catalog = installedDomainCatalog(*installed);
        const auto manifests = installedDomainManifests();
        check(catalog.catalogs.size() == 27 && manifests.size() == 27, "twenty-seven exact installed domain bundles");
        check(catalog.catalogs[0].entries.size() == 6 && catalog.catalogs[1].entries.size() == 2
            && catalog.catalogs[2].entries.size() == 2 && catalog.catalogs[3].entries.size() == 2
            && catalog.catalogs[4].entries.size() == 2 && catalog.catalogs[5].entries.size() == 2
            && catalog.catalogs[6].entries.size() == 2 && catalog.catalogs[7].entries.size() == 2
            && catalog.catalogs[8].entries.size() == 2 && catalog.catalogs[9].entries.size() == 4
            && catalog.catalogs[10].entries.size() == 4 && catalog.catalogs[11].entries.size() == 4
            && catalog.catalogs[12].entries.size() == 4 && catalog.catalogs[13].entries.size() == 2
            && catalog.catalogs[14].entries.size() == 4 && catalog.catalogs[15].entries.size() == 4
            && catalog.catalogs[16].entries.size() == 4 && catalog.catalogs[17].entries.size() == 6
            && catalog.catalogs[18].entries.size() == 2 && catalog.catalogs[19].entries.size() == 6
            && catalog.catalogs[20].entries.size() == 2 && catalog.catalogs[21].entries.size() == 2
            && catalog.catalogs[22].entries.size() == 2 && catalog.catalogs[23].entries.size() == 2
            && catalog.catalogs[24].entries.size() == 2 && catalog.catalogs[25].entries.size() == 2 && catalog.catalogs[26].entries.size() == 2,
            "seventy-eight Practice eligible variants across thirty-eight cases");
        check(catalog.catalogs[3].entries[0].binding.variant == "fg:variant:007408"
            && catalog.catalogs[3].entries[1].binding.variant == "fg:variant:007409"
            && catalog.catalogs[4].entries[0].binding.variant == "fg:variant:007410"
            && catalog.catalogs[4].entries[1].binding.variant == "fg:variant:007411"
            && catalog.catalogs[5].entries[0].binding.variant == "fg:variant:007412"
            && catalog.catalogs[5].entries[1].binding.variant == "fg:variant:007413"
            && catalog.catalogs[6].entries[0].binding.variant == "fg:variant:007414"
            && catalog.catalogs[6].entries[1].binding.variant == "fg:variant:007415"
            && catalog.catalogs[7].entries[0].binding.variant == "fg:variant:007416"
            && catalog.catalogs[7].entries[1].binding.variant == "fg:variant:007417"
            && catalog.catalogs[8].entries[0].binding.variant == "fg:variant:007418"
            && catalog.catalogs[8].entries[1].binding.variant == "fg:variant:007419"
            && catalog.catalogs[9].entries[0].binding.item == "fg:item:001149"
            && catalog.catalogs[9].entries[0].binding.variant == "fg:variant:007420"
            && catalog.catalogs[9].entries[1].binding.variant == "fg:variant:007421"
            && catalog.catalogs[9].entries[2].binding.item == "fg:item:001150"
            && catalog.catalogs[9].entries[2].binding.variant == "fg:variant:007422"
            && catalog.catalogs[9].entries[3].binding.variant == "fg:variant:007423"
            && catalog.catalogs[10].entries[0].binding.item == "fg:item:001151"
            && catalog.catalogs[10].entries[0].binding.variant == "fg:variant:007424"
            && catalog.catalogs[10].entries[1].binding.variant == "fg:variant:007425"
            && catalog.catalogs[10].entries[2].binding.item == "fg:item:001152"
            && catalog.catalogs[10].entries[2].binding.variant == "fg:variant:007426"
            && catalog.catalogs[10].entries[3].binding.variant == "fg:variant:007427"
            && catalog.catalogs[11].entries[0].binding.item == "fg:item:001153"
            && catalog.catalogs[11].entries[0].binding.variant == "fg:variant:007428"
            && catalog.catalogs[11].entries[1].binding.variant == "fg:variant:007429"
            && catalog.catalogs[11].entries[2].binding.item == "fg:item:001154"
            && catalog.catalogs[11].entries[2].binding.variant == "fg:variant:007430"
            && catalog.catalogs[11].entries[3].binding.variant == "fg:variant:007431"
            && catalog.catalogs[12].entries[0].binding.item == "fg:item:001155"
            && catalog.catalogs[12].entries[0].binding.variant == "fg:variant:007432"
            && catalog.catalogs[12].entries[1].binding.variant == "fg:variant:007433"
            && catalog.catalogs[12].entries[2].binding.item == "fg:item:001156"
            && catalog.catalogs[12].entries[2].binding.variant == "fg:variant:007434"
            && catalog.catalogs[12].entries[3].binding.variant == "fg:variant:007435"
            && catalog.catalogs[13].entries[0].binding.item == "fg:item:001157"
            && catalog.catalogs[13].entries[0].binding.variant == "fg:variant:007436"
            && catalog.catalogs[13].entries[1].binding.variant == "fg:variant:007437"
            && catalog.catalogs[14].entries[0].binding.item == "fg:item:001158"
            && catalog.catalogs[14].entries[0].binding.variant == "fg:variant:007438"
            && catalog.catalogs[14].entries[1].binding.variant == "fg:variant:007439"
            && catalog.catalogs[14].entries[2].binding.item == "fg:item:001159"
            && catalog.catalogs[14].entries[2].binding.variant == "fg:variant:007440"
            && catalog.catalogs[14].entries[3].binding.variant == "fg:variant:007441"
            && catalog.catalogs[15].entries[0].binding.item == "fg:item:001160"
            && catalog.catalogs[15].entries[0].binding.variant == "fg:variant:007442"
            && catalog.catalogs[15].entries[1].binding.variant == "fg:variant:007443"
            && catalog.catalogs[15].entries[2].binding.item == "fg:item:001161"
            && catalog.catalogs[15].entries[2].binding.variant == "fg:variant:007444"
            && catalog.catalogs[15].entries[3].binding.variant == "fg:variant:007445"
            && catalog.catalogs[16].entries[0].binding.item == "fg:item:001162"
            && catalog.catalogs[16].entries[0].binding.variant == "fg:variant:007446"
            && catalog.catalogs[16].entries[1].binding.variant == "fg:variant:007447"
            && catalog.catalogs[16].entries[2].binding.item == "fg:item:001163"
            && catalog.catalogs[16].entries[2].binding.variant == "fg:variant:007448"
            && catalog.catalogs[16].entries[3].binding.variant == "fg:variant:007449"
            && catalog.catalogs[17].entries[0].binding.item == "fg:item:001164"
            && catalog.catalogs[17].entries[0].binding.variant == "fg:variant:007450"
            && catalog.catalogs[17].entries[1].binding.variant == "fg:variant:007451"
            && catalog.catalogs[17].entries[2].binding.item == "fg:item:001165"
            && catalog.catalogs[17].entries[2].binding.variant == "fg:variant:007452"
            && catalog.catalogs[17].entries[3].binding.variant == "fg:variant:007453"
            && catalog.catalogs[17].entries[4].binding.item == "fg:item:001166"
            && catalog.catalogs[17].entries[4].binding.variant == "fg:variant:007454"
            && catalog.catalogs[17].entries[5].binding.variant == "fg:variant:007455"
            && catalog.catalogs[18].entries[0].binding.item == "fg:item:001167"
            && catalog.catalogs[18].entries[0].binding.variant == "fg:variant:007456"
            && catalog.catalogs[18].entries[1].binding.variant == "fg:variant:007457"
            && catalog.catalogs[19].entries[0].binding.item == "fg:item:001168"
            && catalog.catalogs[19].entries[0].binding.variant == "fg:variant:007458"
            && catalog.catalogs[19].entries[1].binding.variant == "fg:variant:007459"
            && catalog.catalogs[19].entries[2].binding.item == "fg:item:001169"
            && catalog.catalogs[19].entries[2].binding.variant == "fg:variant:007460"
            && catalog.catalogs[19].entries[3].binding.variant == "fg:variant:007461"
            && catalog.catalogs[19].entries[4].binding.item == "fg:item:001170"
            && catalog.catalogs[19].entries[4].binding.variant == "fg:variant:007462"
            && catalog.catalogs[19].entries[5].binding.variant == "fg:variant:007463",
            "prior through Level21 exact D/U case bindings");
        check(catalog.catalogs[20].contentManifestSha256 ==
                "ac8020af955cef93d8f2aa886edad93bd440e4b5c64b038a2e3f332b6f13df44"
            && catalog.catalogs[20].entries[0].binding.item == "fg:item:001171"
            && catalog.catalogs[20].entries[0].binding.variant == "fg:variant:007464"
            && catalog.catalogs[20].entries[1].binding.variant == "fg:variant:007465"
            && catalog.catalogs[20].entries[0].binding.contentVersion ==
                "curriculum-v1-level022-first-neighbor-pair-build-only.1"
            && catalog.catalogs[20].entries[0].provenanceSha256 ==
                "0031bdd05834d1f1f381240a48a5fa193da561f7bdf51df580771f593c82b1dc"
            && catalog.catalogs[20].entries[0].supportingSha256 ==
                "f07518814be26b8290c6b9a688251eb77fd2b2aedb8efc03a0469167d8be7bde",
            "Level22 pair has exact domain binding and original TXT/PDF authority");
        check(catalog.catalogs[21].contentManifestSha256 ==
                "4d0fea8ad4971ea9ef8155e63fad4b72c176ee9c2f5f1b93689f99d634adce41"
            && catalog.catalogs[21].entries[0].binding.item == "fg:item:001172"
            && catalog.catalogs[21].entries[0].binding.variant == "fg:variant:007466"
            && catalog.catalogs[21].entries[1].binding.variant == "fg:variant:007467"
            && catalog.catalogs[21].entries[0].binding.contentVersion ==
                "curriculum-v1-level023-first-rolling-cell-build-only.1"
            && catalog.catalogs[21].entries[0].provenanceSha256 ==
                "c8c01c4a4ad95e1aed5323d485b359a1bd4d057f46fd2b3ffe8277324b0032f7"
            && catalog.catalogs[21].entries[0].supportingSha256 ==
                "5601a14c406f3b33e455e96d4539ade22160ed0ac95aa782b36a2ef9d960dd43",
            "Level23 first cell has exact recorded-domain and TXT/PDF authority");
        check(catalog.catalogs[22].contentManifestSha256 ==
                "af0d6891254eb23b1e7fcd45dfb236e3f3a7b1982b96cb80bddad8891b110145"
            && catalog.catalogs[22].sourceManifestSha256 ==
                "058e70b6b21b82d07f4af77bbf3eb5f505669e920d7031757257d03b543a48ad"
            && catalog.catalogs[22].entries[0].binding.item == "fg:item:001173"
            && catalog.catalogs[22].entries[0].binding.variant == "fg:variant:007468"
            && catalog.catalogs[22].entries[1].binding.variant == "fg:variant:007469"
            && catalog.catalogs[22].entries[0].binding.contentVersion ==
                "curriculum-v1-level024-first-linked-cell-build-only.1"
            && catalog.catalogs[22].entries[0].provenanceSha256 ==
                "2a91403130355b916d2d935a2df197cbe54a03d1d17cb32575ad6df73bee9988"
            && catalog.catalogs[22].entries[0].supportingSha256 ==
                "6f447ad03a5a0b21cee9ea20ab2cb561e9fb25f5cd7c6a5e8a5121b7657697ad",
            "Level24 first linked cell has exact recorded-domain and source manifest authority");
        check(catalog.catalogs[23].contentManifestSha256 == "d43ea87a1e1663b42b38a9078d26e3c241b55c9924c5e1ef11efb72a0e7254e4"
            && catalog.catalogs[23].sourceManifestSha256 == "8508e52bd71e11cbc5fca449f70f420630b514af7e2e5ee17de935f399a91662"
            && catalog.catalogs[23].entries[0].binding.item == "fg:item:001174"
            && catalog.catalogs[23].entries[0].binding.variant == "fg:variant:007470"
            && catalog.catalogs[23].entries[1].binding.variant == "fg:variant:007471"
            && catalog.catalogs[23].entries[0].binding.contentVersion == "curriculum-v1-level030-first12-build-only.1"
            && catalog.catalogs[23].entries[0].provenanceSha256 == "98e748f4dc9626eb2e4ad63888e503ae5599ea88c01494ebb231d4baa30fc9c9"
            && catalog.catalogs[23].entries[0].supportingSha256 == "40a0ccb47e7fd9ec4c3f47653a309e05921505fdacabbe7646f19a2b687c8c7b",
            "Level30 first12 has exact recorded-domain and source manifest authority");
        check(catalog.catalogs[24].contentManifestSha256 == "e20e9f4a834e80257952e08d62a5befdd2ab96d76943495f2cb29148fc0c34f7"
            && catalog.catalogs[24].sourceManifestSha256 == "b938cb02d06b1f7bb55d0ad76e5786d81effdde3c30ead98f814c096f2d73fe9"
            && catalog.catalogs[24].entries[0].binding.item == "fg:item:001175"
            && catalog.catalogs[24].entries[0].binding.variant == "fg:variant:007472"
            && catalog.catalogs[24].entries[1].binding.variant == "fg:variant:007473"
            && catalog.catalogs[24].entries[0].binding.contentVersion == "curriculum-v1-level029-module1-first30-build-only.1"
            && catalog.catalogs[24].entries[0].provenanceSha256 == "543d98fa9279f39d8975d6b00cd43e5f5aebbb94c5e59fe7771f63af8d8244e5"
            && catalog.catalogs[24].entries[0].supportingSha256 == "2310fc942262081445d80d164ae6feab6335a879db283863db27f69bb75ef445",
            "Level29 Module1 first30 has exact recorded-domain and source manifest authority");
        check(catalog.catalogs[25].contentManifestSha256 == "1d04798658aec24e1bafe698e27a7eaec54f1714cd58ae02ce5efd6f057a5705"
            && catalog.catalogs[25].sourceManifestSha256 == "fd1c69e66fef01546f19e6b9dfafc05c7b319f8fd96bc7fc972febc7a49f6f61"
            && catalog.catalogs[25].entries[0].binding.item == "fg:item:001176"
            && catalog.catalogs[25].entries[0].binding.variant == "fg:variant:007474"
            && catalog.catalogs[25].entries[1].binding.variant == "fg:variant:007475"
            && catalog.catalogs[25].entries[0].binding.contentVersion == "curriculum-v1-level025-first-cell-build-only.1"
            && catalog.catalogs[25].entries[0].provenanceSha256 == "707c3edbfe942f703e94a7a7bd067215124e7ac4e5eb008c891e7c62102c30bb"
            && catalog.catalogs[25].entries[0].supportingSha256 == "7b0f5f718c79123a0515637dcbe01b6c3224ea1047e985f9e369a8618521aede"
            && catalog.catalogs[25].entries[0].domains == std::vector<std::string>{"Technique/fretboard"}
            && catalog.catalogs[25].entries[1].domains == std::vector<std::string>{"Technique/fretboard"},
            "Level25 first40 D/U variants have exact recorded-only domain and source authority");
        check(catalog.catalogs[26].contentManifestSha256 == "fad56ca8236664503a9c6ce6c148a99502972b31b5b46b61b5250663af6f6082"
            && catalog.catalogs[26].sourceManifestSha256 == "89da940807a1982b67550b25b2cb054f173c0fcf7bd122eb2589d5b47562987c"
            && catalog.catalogs[26].entries[0].binding.item == "fg:item:001177"
            && catalog.catalogs[26].entries[0].binding.variant == "fg:variant:007476"
            && catalog.catalogs[26].entries[1].binding.variant == "fg:variant:007477"
            && catalog.catalogs[26].entries[0].binding.contentVersion == "curriculum-v1-level026-first-cell-build-only.1"
            && catalog.catalogs[26].entries[0].provenanceSha256 == "816ef6a286175efe575ee93d14224aaaf44111af3ea58a73f6787898b478c0f5"
            && catalog.catalogs[26].entries[0].supportingSha256 == "c00d5751bb301d4a6b5bb66e009376218226fc90cb7f2d2fb0abbc2e0c9697d8"
            && catalog.catalogs[26].entries[0].domains == std::vector<std::string>{"Technique/fretboard"}
            && catalog.catalogs[26].entries[1].domains == std::vector<std::string>{"Technique/fretboard"},
            "Level26 first96 D/U variants have exact recorded-only domain and source authority");
        check(catalog.catalogs[4].entries[0].provenanceSha256
                == "bbd337b205eac66e474b7b90dea7c5e18c35fe6f09eec7aee3a058f1c0eb4d19"
            && catalog.catalogs[4].entries[0].supportingSha256
                == "a2b97e01ad98bc4e01dfeccfb799b19a5c3c712c233cc9def5e8d95ca16aaac8",
            "Level6 source and PDF authority remain distinct from Level12");
        check(catalog.catalogs[5].contentManifestSha256
                == "677d50fa1e2e7dea63ab69139943bf16e719c6af3383e6c751902ddcdd21503b"
            && catalog.catalogs[5].entries[0].binding.contentVersion
                == "curriculum-v1-level012-rung05-local-build-only.1"
            && catalog.catalogs[5].entries[0].provenanceSha256
                == "64e65f5293012f9af3c84a885cbdd54c82275f6c6e282c8f8a28cca579631be9"
            && catalog.catalogs[5].entries[0].supportingSha256
                == "ae31f029a3df324baa8822b913deb499eccc1438f1986967f96889e6eb45bd3b",
            "Rung05 bundle, version, original TXT and PDF bound exactly");
        check(catalog.catalogs[6].contentManifestSha256
                == "d4c44f1b6745a710b702b5a1fd21e97bb11365699ae5a0795ba5dba5a64ea225"
            && catalog.catalogs[6].entries[0].binding.contentVersion
                == "curriculum-v1-level008-ex001-first-shift-build-only.1"
            && catalog.catalogs[6].entries[0].provenanceSha256
                == "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a"
            && catalog.catalogs[6].entries[0].supportingSha256
                == "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829",
            "Level8 bundle, version, original TXT and PDF bound exactly");
        const auto level8Identity = installed->admit("fg:item:001146", "fg:variant:007414")->identity();
        check(level8Identity.object().at("source_hashes").object().at("L8-PDF1-p2")
                == json::Value("750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829")
            && level8Identity.object().at("source_hashes").object().at("L8-PDF1-p1")
                == json::Value("750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829"),
            "both ordered Level8 PDF references retain original source hash");
        check(catalog.catalogs[7].contentManifestSha256
                == "acd3277998a19da2db8ed2cdbde84c39f29ad725fae56fbcda5c8673a9c6b35e"
            && catalog.catalogs[7].entries[0].binding.contentVersion
                == "curriculum-v1-level010-ex001-first-odd-shift-build-only.1"
            && catalog.catalogs[7].entries[0].provenanceSha256
                == "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226"
            && catalog.catalogs[7].entries[0].supportingSha256
                == "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b",
            "Level10 bundle, version, original TXT and PDF bound exactly");
        const auto level10Identity = installed->admit("fg:item:001147", "fg:variant:007416")->identity();
        check(level10Identity.object().at("source_hashes").object().at("L10-PDF1-p2")
                == json::Value("1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b")
            && level10Identity.object().at("source_hashes").object().at("L10-PDF1-p1")
                == json::Value("1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b"),
            "both ordered Level10 PDF references retain original source hash");
        check(catalog.catalogs[8].contentManifestSha256
                == "d9d788a8cf7facf5afb97874eb4c169589b898397d5f896d437f4b27e3338b9e"
            && catalog.catalogs[8].entries[0].binding.contentVersion
                == "curriculum-v1-level007-ex001-relay-pass2-build-only.1"
            && catalog.catalogs[8].entries[0].provenanceSha256
                == "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61"
            && catalog.catalogs[8].entries[0].supportingSha256
                == "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea",
            "Level7 bundle, version, original TXT and PDF bound exactly");
        const auto level7Identity = installed->admit("fg:item:001148", "fg:variant:007418")->identity();
        check(level7Identity.object().at("source_hashes").object().at("L7-PDF1-p2")
                == json::Value("5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea")
            && level7Identity.object().at("source_hashes").object().at("L7-PDF1-p1")
                == json::Value("5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea"),
            "both ordered Level7 PDF references retain original source hash");
        check(catalog.catalogs[9].contentManifestSha256
                == "39e597135613e695285df0048ef3bc7babdbf13633b5af6e711268bd7025b313"
            && catalog.catalogs[9].entries[0].binding.contentVersion
                == "curriculum-v1-level009-ex001-first-up-down-pass2-build-only.1"
            && catalog.catalogs[9].entries[0].provenanceSha256
                == "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105"
            && catalog.catalogs[9].entries[0].supportingSha256
                == "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f"
            && catalog.catalogs[9].entries[2].binding.contentVersion
                == catalog.catalogs[9].entries[0].binding.contentVersion,
            "both Level9 cases share one exact installed bundle, version, original TXT and PDF");
        for(const auto& selected : std::array<std::pair<const char*,const char*>,2>{{
                {"fg:item:001149","fg:variant:007420"},{"fg:item:001150","fg:variant:007422"}}}) {
            const auto identity = installed->admit(selected.first, selected.second)->identity();
            check(identity.object().at("source_hashes").object().at("L9-PDF1-p2")
                    == json::Value("3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f")
                && identity.object().at("source_hashes").object().at("L9-PDF1-p1")
                    == json::Value("3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f"),
                "both ordered Level9 PDF references retain original source hash");
        }
        check(catalog.catalogs[13].contentManifestSha256
                == "e132f1c3117df3515457adb53058227f1878e2032c9ea6684d301af7cb2c4ccc"
            && catalog.catalogs[13].entries[0].binding.contentVersion
                == "curriculum-v1-level015-rung01-complete-triplet-build-only.1"
            && catalog.catalogs[13].entries[0].provenanceSha256
                == "896937c0d5040c8e7590364433e141bbe7f6da419e063a8ed2590666d5a2c514"
            && catalog.catalogs[13].entries[0].supportingSha256
                == "9c3e2b980079fb3a4eca7affe9bc948a2e58cab15f256766976451ac08d53a5e",
            "Level15 complete cell binds exact installed bundle and original TXT/PDF");
        const auto l15Identity = installed->admit("fg:item:001157", "fg:variant:007436")->identity();
        for(const char* ref:{"L15-PDF-GUIDANCE-P1","L15-PDF-CARD-P3"})
            check(l15Identity.object().at("source_hashes").object().at(ref)
                == json::Value("9c3e2b980079fb3a4eca7affe9bc948a2e58cab15f256766976451ac08d53a5e"),
                "Level15 ordered PDF source hash remains exact");
        check(catalog.catalogs[10].contentManifestSha256
                == "5dfcfda497684bc267901eb794bb1d92476db17003f7914a7b3d0bc99007ea21"
            && catalog.catalogs[10].entries[0].binding.contentVersion
                == "curriculum-v1-level011-ex001-first-up-down-pass2-build-only.1"
            && catalog.catalogs[10].entries[0].provenanceSha256
                == "e579bb423d644a628723c802d84967f5c7aad49bf4e8e89bba5e4b622bf6ff48"
            && catalog.catalogs[10].entries[0].supportingSha256
                == "5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917"
            && catalog.catalogs[10].entries[2].binding.contentVersion
                == catalog.catalogs[10].entries[0].binding.contentVersion,
            "both Level11 cases share exact bundle, version, original TXT and PDF");
        for(const auto& selected : std::array<std::pair<const char*,const char*>,2>{{
                {"fg:item:001151","fg:variant:007424"},{"fg:item:001152","fg:variant:007426"}}}) {
            const auto identity = installed->admit(selected.first, selected.second)->identity();
            check(identity.object().at("source_hashes").object().at("L11-PDF1-p2")
                    == json::Value("5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917")
                && identity.object().at("source_hashes").object().at("L11-PDF1-p1")
                    == json::Value("5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917"),
                "both ordered Level11 PDF references retain original source hash");
        }
        check(catalog.catalogs[11].contentManifestSha256
                == "e0edd51ab639c58b6421f3ad5cd14fd57585129d8377c10cdb9f6e8eca053b6b"
            && catalog.catalogs[11].entries[0].binding.contentVersion
                == "curriculum-v1-level013-rung01-a-and-a-bb-timed-build-only.1"
            && catalog.catalogs[11].entries[0].provenanceSha256
                == "973b9c614546e432282dcc0ba415a21c0bc28858e61e7910ef2d0559329a0956"
            && catalog.catalogs[11].entries[0].supportingSha256
                == "0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c"
            && catalog.catalogs[11].entries[2].binding.contentVersion
                == catalog.catalogs[11].entries[0].binding.contentVersion,
            "both Level13 cases bind one exact installed bundle, original TXT/PDF and version");
        for(const auto& selected : std::array<std::pair<const char*,const char*>,2>{{
                {"fg:item:001153","fg:variant:007428"},{"fg:item:001154","fg:variant:007430"}}}) {
            const auto identity = installed->admit(selected.first, selected.second)->identity();
            check(identity.object().at("source_hashes").object().at("L13-PDF-GUIDANCE-P1")
                    == json::Value("0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c")
                && identity.object().at("source_hashes").object().at("L13-PDF-CARDS-P3")
                    == json::Value("0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c"),
                "both ordered Level13 PDF references retain original source hash");
        }
        check(catalog.catalogs[12].contentManifestSha256
                == "51851db9a08f16dbc8ffbd007aff5021bab42bc5404cca54c25c27144d82fc59"
            && catalog.catalogs[12].entries[0].binding.contentVersion
                == "curriculum-v1-level014-rung01-a-and-a-bb-triplet-build-only.1"
            && catalog.catalogs[12].entries[0].provenanceSha256
                == "301edb98b64daa90a015a3560b8c2219cfab13984d6a8c320765af48f444912b"
            && catalog.catalogs[12].entries[0].supportingSha256
                == "c5ec5b0d1ed50c0c8af758a021f4488c886a1c6030c8a5a52cb755471ae7ed19",
            "Level14 pair binds exact installed bundle and original TXT/PDF");
        for(const auto& selected : std::array<std::pair<const char*,const char*>,2>{{
                {"fg:item:001155","fg:variant:007432"},{"fg:item:001156","fg:variant:007434"}}}) {
            const auto hashes = installed->admit(selected.first, selected.second)->identity().object().at("source_hashes");
            for(const char* ref:{"L14-PDF-GUIDANCE-P1","L14-PDF-CARDS-P3","L14-PDF-ROUTE-P2"})
                check(hashes.object().at(ref) == json::Value("c5ec5b0d1ed50c0c8af758a021f4488c886a1c6030c8a5a52cb755471ae7ed19"),
                    "Level14 PDF source hash remains exact");
        }
        check(catalog.catalogs[16].contentManifestSha256
                == "03adee5e7d46bbb1ed4815044c6b9f6db8137c3215fc1e3db427461707210c69"
            && catalog.catalogs[16].entries[0].binding.contentVersion
                == "curriculum-v1-level018-first-two-cases-build-only.1"
            && catalog.catalogs[16].entries[0].provenanceSha256
                == "a4faf2579a2d3546e2dc021640eeb3764ec7de9d858975a66f29f9611e2ad3a8"
            && catalog.catalogs[16].entries[0].supportingSha256
                == "a79374066ff017c148c11ec75791b02ba930560123dde1a6fcc933fe17821536",
            "Level18 pair binds exact installed bundle and original TXT/PDF");
        for(const auto& selected : std::array<std::pair<const char*,const char*>,2>{{
                {"fg:item:001162","fg:variant:007446"},{"fg:item:001163","fg:variant:007448"}}}) {
            const auto hashes = installed->admit(selected.first, selected.second)->identity().object().at("source_hashes");
            for(const char* ref:{"L18-PDF-GUIDANCE","L18-PDF-CARDS","L18-PDF-ROUTE"})
                check(hashes.object().at(ref) == json::Value("a79374066ff017c148c11ec75791b02ba930560123dde1a6fcc933fe17821536"),
                    "Level18 PDF source hash remains exact");
        }
        for (const auto& member : catalog.catalogs)
            for (const auto& entry : member.entries)
                check(entry.domains == std::vector<std::string>{"Technique/fretboard"}
                    && !entry.provenanceSha256.empty() && !entry.supportingSha256.empty()
                    && !entry.vocabularySha256.empty(), "source and vocabulary bound explicit domain");
        refuses([&] { installedDomainCatalog(*lesson::Catalog::load(resources / "representative-controls")); },
                "partial installed Catalog cannot assert all seven cases");
        refuses([&] { installedDomainCatalog(*lesson::Catalog::load(resources / "representative-controls",
            resources / "rung02-extension", resources / "rung03-extension", resources / "rung04-extension")); },
            "without Level6 installed admission the proposed six-case catalog refuses");
        refuses([&] { installedDomainCatalog(*lesson::Catalog::load(resources / "representative-controls",
            resources / "rung02-extension", resources / "rung03-extension",
            resources / "rung04-extension", resources / "level006-extension")); },
            "without Rung05 installed admission the current seven-case catalog refuses");
        refuses([&] { installed->admit("fg:item:000002", "fg:variant:000005"); },
                "unadmitted original variant remains refused");
        refuses([&] { installed->admit("fg:item:001144", "fg:variant:007412"); },
                "Level6 may not claim a foreign variant");
        refuses([&] { installed->admit("fg:item:001145", "fg:variant:007411"); },
                "Rung05 may not claim a foreign variant");

        storage::StoreOptions options;
        options.path = scratch / "profile.sqlite";
        options.create = true;
        options.createdUtc = "2026-09-23T00:00:00Z";
        options.sourceValidator = [](const json::Value&) { return true; }; // Disposable synthetic envelopes only.
        storage::ProfileStore store(options);
        const auto attemptFixture = read(fixtures / "attempt.json");
        const std::array<const DomainBinding*, 20> bindings{{
            &catalog.catalogs[0].entries[0].binding, &catalog.catalogs[0].entries[4].binding,
            &catalog.catalogs[1].entries[0].binding, &catalog.catalogs[2].entries[0].binding,
            &catalog.catalogs[3].entries[0].binding, &catalog.catalogs[3].entries[1].binding,
            &catalog.catalogs[4].entries[0].binding, &catalog.catalogs[4].entries[1].binding,
            &catalog.catalogs[5].entries[0].binding, &catalog.catalogs[5].entries[1].binding,
            &catalog.catalogs[6].entries[0].binding, &catalog.catalogs[6].entries[1].binding,
            &catalog.catalogs[10].entries[0].binding, &catalog.catalogs[10].entries[1].binding,
            &catalog.catalogs[10].entries[2].binding, &catalog.catalogs[10].entries[3].binding,
            &catalog.catalogs[12].entries[0].binding, &catalog.catalogs[12].entries[1].binding,
            &catalog.catalogs[12].entries[2].binding, &catalog.catalogs[12].entries[3].binding}};
        int index = 0;
        for (const auto* binding : bindings) {
            const int minute = index++;
            const auto stamp = std::string("2026-09-23T00:") + (minute < 10 ? "0" : "") + std::to_string(minute) + ":00Z";
            save(store, preparedAttempt(attemptFixture, *binding, *installed), "Attempt", stamp);
        }
        save(store, read(fixtures / "freeplay.json"), "FreeplayActivity", "2026-09-23T00:20:00Z");
        const auto reply = confirmed(store.snapshot("mixed-manifest-confirmed"));
        const auto before = reply.data;
        const auto profile = reply.data.object().at("profile_id").string();
        const auto projected = projectDomainCoverage(reply, catalog, profile, manifests);
        check(projected.mappedAttempts == 20 && projected.ignoredFreeplay == 1
            && projected.unmapped.empty(), "confirmed mixed Store maps eight current cases including Level8 D/U once; Freeplay separate");
        check(projected.byDomain.size() == 1
            && projected.byDomain.at("Technique/fretboard").attempts == 20
            && projected.byDomain.at("Technique/fretboard").activeSeconds == Rational(80),
            "twenty source-bound Attempts aggregate exact active time without duplicate credit");
        check(projected.profile == profile && projected.catalogSha256.size() == 64
            && projected.evidenceSha256.size() == 64 && projected.snapshotSha256.size() == 64,
            "profile, catalog, evidence and snapshot identity retained");
        check(confirmed(store.snapshot("mixed-manifest-after-read")).data.object().at("authoritative")
            == before.object().at("authoritative"), "projection leaves authoritative Store facts untouched");

        auto snapshot = adaptSnapshot(reply);
        std::vector<std::size_t> attemptIndices;
        for (std::size_t i = 0; i < snapshot.records.size(); ++i)
            if (snapshot.records[i].kind == Kind::Attempt) attemptIndices.push_back(i);
        check(attemptIndices.size() == 20, "confirmed snapshot contains twenty distinct Attempts");
        auto historical = snapshot;
        historical.records[attemptIndices[0]].sourceScope.object()["content_version"] = "historical-version";
        historical.records[attemptIndices[1]].sourceScope.object()["source_manifest_sha256"] = std::string(64, 'f');
        historical.records[attemptIndices[2]].sourceScope.object()["source_refs"] = json::Value::Array{"foreign-ref"};
        const auto unmapped = projectDomainCoverage(historical, catalog, profile, manifests);
        check(unmapped.mappedAttempts == 17 && unmapped.unmapped.size() == 3
            && unmapped.unmapped[0].reason == "content_version_mismatch"
            && unmapped.unmapped[1].reason == "source_manifest_mismatch"
            && unmapped.unmapped[2].reason == "source_refs_mismatch",
            "changed version, source manifest and refs retain original owners as unmapped");
        historical = snapshot;
        historical.records[attemptIndices[0]].sourceScope.object()["item_id"] = "fg:item:999999";
        historical.records[attemptIndices[1]].sourceScope.object()["variant_id"] = "fg:variant:999999";
        historical.records[attemptIndices[2]].sourceScope.object()["content_revision"] = json::Value::fromInteger(99);
        const auto unknown = projectDomainCoverage(historical, catalog, profile, manifests);
        check(unknown.mappedAttempts == 17 && unknown.unmapped.size() == 3
            && unknown.unmapped[0].reason == "unknown_item"
            && unknown.unmapped[1].reason == "unknown_variant"
            && unknown.unmapped[2].reason == "content_revision_mismatch",
            "unadmitted identity and older/changed revision remain unmapped");
        auto bad = catalog;
        bad.catalogs[1].entries.push_back(bad.catalogs[1].entries[0]);
        refuses([&] { projectDomainCoverage(snapshot, bad, profile, manifests); }, "duplicate binding refused");
        bad = catalog;
        bad.catalogs[1].entries[0].binding.item = bad.catalogs[0].entries[0].binding.item;
        bad.catalogs[1].entries[0].binding.variant = bad.catalogs[0].entries[0].binding.variant;
        refuses([&] { projectDomainCoverage(snapshot, bad, profile, manifests); }, "mixed-version owner collision refused");
        bad = catalog;
        bad.catalogs[1].entries[0].binding.item = bad.catalogs[0].entries[0].binding.item;
        refuses([&] { projectDomainCoverage(snapshot, bad, profile, manifests); }, "same item in second bundle refused");
        bad = catalog;
        bad.catalogs[1].entries[0].binding.variant = bad.catalogs[0].entries[0].binding.variant;
        refuses([&] { projectDomainCoverage(snapshot, bad, profile, manifests); }, "duplicate variant owner refused");
        bad = catalog;
        bad.catalogs[1].contentManifestSha256 = std::string(64, 'f');
        refuses([&] { projectDomainCoverage(snapshot, bad, profile, manifests); }, "changed bundle manifest refused");
        historical = snapshot;
        historical.records[attemptIndices[6]].sourceScope.object()["source_refs"] = json::Value::Array{"foreign-level6-ref"};
        const auto changedLevel6Source = projectDomainCoverage(historical, catalog, profile, manifests);
        check(changedLevel6Source.mappedAttempts == 19 && changedLevel6Source.unmapped.size() == 1
            && changedLevel6Source.unmapped[0].reason == "source_refs_mismatch",
            "changed Level6 source binding retains original Attempt owner as unmapped");
        historical = snapshot;
        historical.records[attemptIndices[8]].sourceScope.object()["source_refs"] = json::Value::Array{"foreign-rung05-ref"};
        const auto changedRung05Source = projectDomainCoverage(historical, catalog, profile, manifests);
        check(changedRung05Source.mappedAttempts == 19 && changedRung05Source.unmapped.size() == 1
            && changedRung05Source.unmapped[0].reason == "source_refs_mismatch",
            "changed Rung05 source binding retains original Attempt owner as unmapped");
        historical = snapshot;
        historical.records[attemptIndices[10]].sourceScope.object()["source_refs"] = json::Value::Array{"foreign-level8-ref"};
        const auto changedLevel8Source = projectDomainCoverage(historical, catalog, profile, manifests);
        check(changedLevel8Source.mappedAttempts == 19 && changedLevel8Source.unmapped.size() == 1
            && changedLevel8Source.unmapped[0].reason == "source_refs_mismatch",
            "changed Level8 source binding retains original Attempt owner as unmapped");
        historical = snapshot;
        historical.records[attemptIndices[12]].sourceScope.object()["source_refs"] = json::Value::Array{"foreign-level11-ref"};
        const auto changedLevel11Source = projectDomainCoverage(historical, catalog, profile, manifests);
        check(changedLevel11Source.mappedAttempts == 19 && changedLevel11Source.unmapped.size() == 1
            && changedLevel11Source.unmapped[0].reason == "source_refs_mismatch",
            "changed Level11 source binding retains original Attempt owner as unmapped");
        bad = catalog;
        bad.catalogs[4].entries[0].binding.variant = bad.catalogs[3].entries[0].binding.variant;
        refuses([&] { projectDomainCoverage(snapshot, bad, profile, manifests); }, "new case duplicate variant owner refused");
        refuses([&] { projectDomainCoverage(snapshot, catalog, "foreign-profile", manifests); }, "foreign profile refused");
        refuses([&] { projectDomainCoverage(snapshot, catalog, profile, {manifests[0], manifests[1]}); }, "missing expected manifest refused");
        auto withoutLevel6 = manifests;
        withoutLevel6.erase(withoutLevel6.begin() + 4);
        refuses([&] { projectDomainCoverage(snapshot, catalog, profile, withoutLevel6); }, "missing Level6 manifest refused");
        auto withoutRung05 = manifests;
        withoutRung05.erase(withoutRung05.begin() + 5);
        refuses([&] { projectDomainCoverage(snapshot, catalog, profile, withoutRung05); }, "missing Rung05 manifest refused");
        refuses([&] { projectDomainCoverage(snapshot, catalog, profile, {manifests[0], manifests[1], manifests[1]}); }, "duplicate expected manifest refused");
        auto withoutLevel25 = manifests;
        withoutLevel25.erase(withoutLevel25.begin() + 25);
        refuses([&] { projectDomainCoverage(snapshot, catalog, profile, withoutLevel25); }, "missing Level25 manifest refused");
        auto withoutLevel26 = manifests;
        withoutLevel26.erase(withoutLevel26.begin() + 26);
        refuses([&] { projectDomainCoverage(snapshot, catalog, profile, withoutLevel26); }, "missing Level26 manifest refused");
        auto duplicate = snapshot;
        duplicate.records.push_back(duplicate.records[attemptIndices[0]]);
        refuses([&] { projectDomainCoverage(duplicate, catalog, profile, manifests); }, "duplicate original Attempt owner refused");
        storage::Reply unconfirmed;
        refuses([&] { projectDomainCoverage(unconfirmed, catalog, profile, manifests); }, "unconfirmed Store Reply refused");
        save(store, preparedAttempt(attemptFixture, catalog.catalogs[25].entries[0].binding, *installed),
             "Attempt", "2026-09-23T00:21:00Z");
        save(store, preparedAttempt(attemptFixture, catalog.catalogs[25].entries[1].binding, *installed),
             "Attempt", "2026-09-23T00:22:00Z");
        const auto level25Reply = confirmed(store.snapshot("level25-recorded-activity"));
        const auto level25Mapped = projectDomainCoverage(level25Reply, catalog, profile, manifests);
        check(level25Mapped.mappedAttempts == 22 && level25Mapped.unmapped.empty()
            && level25Mapped.ignoredFreeplay == 1 && level25Mapped.byDomain.size() == 1
            && level25Mapped.byDomain.at("Technique/fretboard").attempts == 22
            && level25Mapped.byDomain.at("Technique/fretboard").activeSeconds == Rational(88),
            "two Level25 D/U Attempts add only recorded Technique/fretboard activity");
        save(store, preparedAttempt(attemptFixture, catalog.catalogs[26].entries[0].binding, *installed),
             "Attempt", "2026-09-23T00:23:00Z");
        save(store, preparedAttempt(attemptFixture, catalog.catalogs[26].entries[1].binding, *installed),
             "Attempt", "2026-09-23T00:24:00Z");
        const auto level26Reply = confirmed(store.snapshot("level26-recorded-activity"));
        const auto level26Mapped = projectDomainCoverage(level26Reply, catalog, profile, manifests);
        check(level26Mapped.mappedAttempts == 24 && level26Mapped.unmapped.empty()
            && level26Mapped.ignoredFreeplay == 1 && level26Mapped.byDomain.size() == 1
            && level26Mapped.byDomain.at("Technique/fretboard").attempts == 24
            && level26Mapped.byDomain.at("Technique/fretboard").activeSeconds == Rational(96),
            "two Level26 D/U Attempts add only recorded Technique/fretboard activity");
        if (argc == 5) {
            storage::StoreOptions actualOptions;
            actualOptions.path = argv[4];
            actualOptions.create = false;
            storage::ProfileStore actual(actualOptions);
            const auto actualReply = confirmed(actual.snapshot("level30-installed-proof-before"));
            const auto actualBefore = actualReply.data.object().at("authoritative");
            const auto actualProfile = actualReply.data.object().at("profile_id").string();
            const auto actualProjection = projectDomainCoverage(actualReply, catalog, actualProfile, manifests);
            check(actualProjection.mappedAttempts == 2 && actualProjection.unmapped.empty()
                && actualProjection.byDomain.size() == 1
                && actualProjection.byDomain.at("Technique/fretboard").attempts == 2
                && actualProjection.ignoredFreeplay == 0,
                "actual installed Level29 two D/U Saves map 2/0 as recorded activity only");
            check(confirmed(actual.snapshot("level30-installed-proof-after")).data.object().at("authoritative")
                == actualBefore, "installed Profile projection does not alter authoritative tables");
        }
        std::cout << "PASS " << checks << " installed domain catalog and mixed Store checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
