#include "progression/InstalledDomainCatalog.hpp"
#include <algorithm>
#include <array>

namespace fathom::progression {
namespace {
constexpr const char* sourceManifest = "e856ef05e610b9be51f33aac661a900301f747a9259bfcbd951b756a247504fe";
constexpr const char* level001SourceManifest = "5b321fcc6df6f88683f34f9e9d344345639dc276503d70da8d53928b4223ce39";
constexpr const char* level001Bundle = "4626ab601fceb4c2727e866e7fd083c674994941d5853f13a812033f58121d65";
constexpr const char* level001Txt = "0f5719945456692fc4c40ce3b06e0cd742b61b7f8615ad465b9f26832cd08842";
constexpr const char* level001Pdf = "3b0ca589c94497d80ce7529018cacb01d6b6fa6982797e61a8228ee044b72d62";
constexpr const char* l3Txt = "1bb8d5225f2db8df2b3ce518f10f28e11158592e0b5cbbb4c28af2742c861b4f";
constexpr const char* l4Txt = "4c90d79866f42125a7aa8785e803462864dbb88b2ecfa856438bf49f922f3d9a";
constexpr const char* l4Pdf = "b24cad79148b8165b74cbd3662031c2ad0227f0e856aa955d03c88db31dbafb1";
constexpr const char* l12Txt = "64e65f5293012f9af3c84a885cbdd54c82275f6c6e282c8f8a28cca579631be9";
constexpr const char* l6Txt = "bbd337b205eac66e474b7b90dea7c5e18c35fe6f09eec7aee3a058f1c0eb4d19";
constexpr const char* l3Pdf = "f04c1e49ce939ec83e5c80f9ad8cc81fd49da62e2039c25cac5367cea0fa6234";
constexpr const char* l12Pdf = "ae31f029a3df324baa8822b913deb499eccc1438f1986967f96889e6eb45bd3b";
constexpr const char* l6Pdf = "a2b97e01ad98bc4e01dfeccfb799b19a5c3c712c233cc9def5e8d95ca16aaac8";
constexpr const char* vocabularySha = "ecc9bd187011862632d826a21802afcef3f2162b6491e857311a6cde6845710f";
constexpr const char* originalBundle = "f57b3c6e1adddd3699bb27c8c0c35f356fbbcb2808f409f87bcca531afa75a8e";
constexpr const char* rung02Bundle = "782c0914adc0d080f3e924219fae3c3fac4b6a6ddb0548c3e32d7668bf8823a0";
constexpr const char* rung03Bundle = "58a1267355da5e039696320cd474057102a4968b4e25933eb3af1ec253cec136";
constexpr const char* rung04Bundle = "cff6c3331f0e31051812fe5a08a463fa0105c711f6a4d9145f4ce6876ee0d1ea";
constexpr const char* level006Bundle = "f7afa661ad0077714a25a062230f534b383cf6df5c9370ab46ebf901ea84b527";
constexpr const char* rung05Bundle = "677d50fa1e2e7dea63ab69139943bf16e719c6af3383e6c751902ddcdd21503b";
constexpr const char* level008Bundle = "d4c44f1b6745a710b702b5a1fd21e97bb11365699ae5a0795ba5dba5a64ea225";
constexpr const char* l8Txt = "0cba6885ed917013d5ceda5e0c231c568b4aa99be4c8c0e23941295a3fa5926a";
constexpr const char* l8Pdf = "750f9b14962e71bc9ed0dc48a6f9343f2a1d5d14363858f7b9462187fc338829";
constexpr const char* level010Bundle = "acd3277998a19da2db8ed2cdbde84c39f29ad725fae56fbcda5c8673a9c6b35e";
constexpr const char* l10Txt = "e5ed078c62295adbb5f6bf00e6821e6eee0b2da73ef42c1714421158b5273226";
constexpr const char* l10Pdf = "1dafdcd177343f0ea147a5479ad654397d85f4b374cf960e264a230db965496b";
constexpr const char* level007Bundle = "d9d788a8cf7facf5afb97874eb4c169589b898397d5f896d437f4b27e3338b9e";
constexpr const char* l7Txt = "467d1401237e34633efc4c517fa98d8190f0b47346a7b34be9d2548924883b61";
constexpr const char* l7Pdf = "5c8607cff40801acb13f5e08dd2988b2ff943593eb084de2801f05f507a6c4ea";
constexpr const char* level009Bundle = "39e597135613e695285df0048ef3bc7babdbf13633b5af6e711268bd7025b313";
constexpr const char* l9Txt = "3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105";
constexpr const char* l9Pdf = "3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f";
constexpr const char* level011Bundle = "5dfcfda497684bc267901eb794bb1d92476db17003f7914a7b3d0bc99007ea21";
constexpr const char* l11Txt = "e579bb423d644a628723c802d84967f5c7aad49bf4e8e89bba5e4b622bf6ff48";
constexpr const char* l11Pdf = "5f9b5e29e2f5ad3aa3372125f0ec0b91e6245eef1edabd5e81c06d1f00f5e917";
constexpr const char* level013Bundle = "e0edd51ab639c58b6421f3ad5cd14fd57585129d8377c10cdb9f6e8eca053b6b";
constexpr const char* l13Txt = "973b9c614546e432282dcc0ba415a21c0bc28858e61e7910ef2d0559329a0956";
constexpr const char* l13Pdf = "0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c";
constexpr const char* level014Bundle = "51851db9a08f16dbc8ffbd007aff5021bab42bc5404cca54c25c27144d82fc59";
constexpr const char* l14Txt = "301edb98b64daa90a015a3560b8c2219cfab13984d6a8c320765af48f444912b";
constexpr const char* l14Pdf = "c5ec5b0d1ed50c0c8af758a021f4488c886a1c6030c8a5a52cb755471ae7ed19";
constexpr const char* level015Bundle = "e132f1c3117df3515457adb53058227f1878e2032c9ea6684d301af7cb2c4ccc";
constexpr const char* l15Txt = "896937c0d5040c8e7590364433e141bbe7f6da419e063a8ed2590666d5a2c514";
constexpr const char* l15Pdf = "9c3e2b980079fb3a4eca7affe9bc948a2e58cab15f256766976451ac08d53a5e";
constexpr const char* level015R0203Bundle = "132c96c283a488142955fc01f3f60c5773dbaad3f7a7a4574200c20381785682";
constexpr const char* level016Bundle = "f9f8ca4ed1cff0c7eef5c4cce690540f397318cb38a4da5cbc7f0212abd3d31d";
constexpr const char* l16Txt = "791020f0cdc3d38d690762b9544d9e3e59bf7caad2ccf81a845f771660b5693c";
constexpr const char* l16Pdf = "20e71408a18593b1ac4da655f9dc2174135ab6caf94240c5f978f3fbf11956aa";
constexpr const char* level017Bundle = "fc741a0a849f4d0d68476e5b6c439e8bc0fa1560fbe6c9ff2595ae6356935f41";
constexpr const char* l17Txt = "e742548015d297941c9972ddb7cfcaeb0a66375b164864698e72d3e0b6bed511";
constexpr const char* l17Pdf = "fc60d519a880c3d6a8a4984d99dd07030fcb56d09f1e2ea9ad951da271349d6d";
constexpr const char* level018Bundle = "03adee5e7d46bbb1ed4815044c6b9f6db8137c3215fc1e3db427461707210c69";
constexpr const char* l18Txt = "a4faf2579a2d3546e2dc021640eeb3764ec7de9d858975a66f29f9611e2ad3a8";
constexpr const char* l18Pdf = "a79374066ff017c148c11ec75791b02ba930560123dde1a6fcc933fe17821536";
constexpr const char* level019Bundle = "13e4bffc017d0356252c7a89ed49715232a11f2107dc90b9a336fae2c2ef491c";
constexpr const char* l19Txt = "d4d0bebee8d9d2b6899bde448a0f5017070eef7936c2ccd6ffa03e7b95a4ce26";
constexpr const char* l19Pdf = "107bfaecd5daa15adc1117440d01feead623f831e720837de5d18662375166e6";
constexpr const char* level020Bundle = "fbdcafadb070ef66e5acea75ff48da0d6b65b5ea5a835a60db9ae5d6ad01fb87";
constexpr const char* l20Txt = "d64e78142630e4b6e22ce49055df87938062d9051eb44d792a1a46448e54d410";
constexpr const char* level021Bundle = "a728e8dc4665edcaa0097cd608457aa4da9a7d20784fe289d5e177582867572f";
constexpr const char* l21Txt = "018db1d53df6b1b175c64d59f95809b3215d055f2c3361c90199ee8f3d75bf67";
constexpr const char* l21Pdf = "b8679699687ef8078f958563ce8f887e8e1083c486ef52d816a09c434d57d235";
constexpr const char* level022Bundle = "ac8020af955cef93d8f2aa886edad93bd440e4b5c64b038a2e3f332b6f13df44";
constexpr const char* l22Txt = "0031bdd05834d1f1f381240a48a5fa193da561f7bdf51df580771f593c82b1dc";
constexpr const char* l22Pdf = "f07518814be26b8290c6b9a688251eb77fd2b2aedb8efc03a0469167d8be7bde";
constexpr const char* level023Bundle = "4d0fea8ad4971ea9ef8155e63fad4b72c176ee9c2f5f1b93689f99d634adce41";
constexpr const char* l23Txt = "c8c01c4a4ad95e1aed5323d485b359a1bd4d057f46fd2b3ffe8277324b0032f7";
constexpr const char* l23Pdf = "5601a14c406f3b33e455e96d4539ade22160ed0ac95aa782b36a2ef9d960dd43";
constexpr const char* level024Bundle = "af0d6891254eb23b1e7fcd45dfb236e3f3a7b1982b96cb80bddad8891b110145";
constexpr const char* l24Txt = "2a91403130355b916d2d935a2df197cbe54a03d1d17cb32575ad6df73bee9988";
constexpr const char* l24Pdf = "6f447ad03a5a0b21cee9ea20ab2cb561e9fb25f5cd7c6a5e8a5121b7657697ad";
constexpr const char* l24SourceManifest = "058e70b6b21b82d07f4af77bbf3eb5f505669e920d7031757257d03b543a48ad";
constexpr const char* level030Bundle = "d43ea87a1e1663b42b38a9078d26e3c241b55c9924c5e1ef11efb72a0e7254e4";
constexpr const char* l30Txt = "98e748f4dc9626eb2e4ad63888e503ae5599ea88c01494ebb231d4baa30fc9c9";
constexpr const char* l30Pdf = "40a0ccb47e7fd9ec4c3f47653a309e05921505fdacabbe7646f19a2b687c8c7b";
constexpr const char* l30SourceManifest = "8508e52bd71e11cbc5fca449f70f420630b514af7e2e5ee17de935f399a91662";
constexpr const char* level029Bundle = "e20e9f4a834e80257952e08d62a5befdd2ab96d76943495f2cb29148fc0c34f7";
constexpr const char* l29Txt = "543d98fa9279f39d8975d6b00cd43e5f5aebbb94c5e59fe7771f63af8d8244e5";
constexpr const char* l29Pdf = "2310fc942262081445d80d164ae6feab6335a879db283863db27f69bb75ef445";
constexpr const char* l29SourceManifest = "b938cb02d06b1f7bb55d0ad76e5786d81effdde3c30ead98f814c096f2d73fe9";
constexpr const char* level025Bundle = "1d04798658aec24e1bafe698e27a7eaec54f1714cd58ae02ce5efd6f057a5705";
constexpr const char* l25Txt = "707c3edbfe942f703e94a7a7bd067215124e7ac4e5eb008c891e7c62102c30bb";
constexpr const char* l25Pdf = "7b0f5f718c79123a0515637dcbe01b6c3224ea1047e985f9e369a8618521aede";
constexpr const char* l25SourceManifest = "fd1c69e66fef01546f19e6b9dfafc05c7b319f8fd96bc7fc972febc7a49f6f61";
constexpr const char* level026Bundle = "fad56ca8236664503a9c6ce6c148a99502972b31b5b46b61b5250663af6f6082";
constexpr const char* level012R08Bundle = "f70287bcf1c86b6e81144f9210e334336a75867af0898b3f2f32ad514441b33f";
constexpr const char* level080R02Bundle = "459d21f648c06be8ce95bf7fbca4590f827632a208034b909eabbd5eb6ce7461";
constexpr const char* level013R03Bundle = "d090d1d4829a2aefcfc321777dfb2039e8a0a0d1471acc74caa5c09b4a96ad94";
constexpr const char* level013R04Bundle = "4c4c30e0c332a23153fa3328dbda72b2d526a270c5bda333e8eb826207184de3";
constexpr const char* level013R05Bundle = "d3a9575f3d385601ea75bee7545fea1526b87b9e6f191f6ecbaa606f3ebdc1d1";
constexpr const char* level015R05Bundle = "a528bee87c570cb7f607bc2db6d5a08e166a7f8834d575aa7d93700cf5057738";
constexpr const char* level015R04Bundle = "3d4762e5dc9e39c285d18d01c04c184359b181ec2d95cd864f5096aa87c332b6";
constexpr const char* level015R06Bundle = "ed0fc4280def665cd14587b44a669200854346d8e7709cf0e648459c553da844";
constexpr const char* level003ModeB001Bundle = "adbef5cd5259b19a4d3d802c4c1d33d7cf3b59bfe09633eef7dbd8c72a5b9a44";
constexpr const char* level004Ex002Bundle = "e860507ab144595233c15ce9c71ebd50874bc39eeba6b46d6143af9b0d961b95";
constexpr const char* level004Ex003Bundle = "5f9894a92b9312f922efcb96929228b46bf59e906a276cb00ee6ea5d838d721d";
constexpr const char* level004Ex004Bundle = "6cb9cf46ac2fab0082a91d857827dbda3ede78137c5f82c1dc040f275054fed7";
constexpr const char* level004Ex005Bundle = "d13028cee25ba99d4fb935207e0c90903e4d903211553b9667f0ade95d9b587f";
constexpr const char* level004Ex006Bundle = "54aef54af5ed5360a66a2c84aaba841ff1b276d6b02d7dd9176e0a341dafb724";
constexpr const char* level004Ex007Bundle = "033fc292658586220977749cbc826d4585c66f2521785454f991179c6bdd16f2";
constexpr const char* level004Ex008Bundle = "eef7e64a6415aa20f3024d9320cfe6f828710a0352ed583b9c7a0f80bd6b7a17";
constexpr const char* level004Ex009Bundle = "0d334155a1854472d3677312e7d169f1410a8a07e8108f1d2a9b7d5483007cc6";
constexpr const char* level004Ex010Bundle = "e0d96d201ce2ac3131d4749c1fed66dad9c8865ea928284046720a5ccf67c98c";
constexpr const char* level004Ex011Bundle = "fc952678ed245b95a0573539990cf0de9d938ac8a35b15ba5ab4fec79aab2337";
constexpr const char* level004Ex012Bundle = "d521768b811d26ea0e792c4a9e4c81e57d0b8026fc0c14d33a346a53ec72c691";
constexpr const char* level004Ex013Bundle = "a8997380778269dd5008b35c2f131f4ed8314ccf8c2f8a57c41a75ae0fe134a2";
constexpr const char* level004Ex014Bundle = "febe1d3475e1160da0e7ecfa6480a3474d109ef6461a1ce344c373c10f60f9f3";
constexpr const char* level004Ex015Bundle = "44414e8085831ad548a44165272455a571dffa34aa5bc2f005df19869dc36e67";
constexpr const char* level002Ex002Bundle = "e65d9bfe567f02aa586e348d97297c9d7982f4745ad57b707f8dbb8f82c0d7d0";
constexpr const char* level002Ex002SourceManifest = "40df3ae433c7e84a2afdde5aa4ead5595e36c2f2ede92648304c7300e51731e1";
constexpr const char* level002Ex002Txt = "49ca027e8c7fee7b2c5437f93f8a5b5576e272e6cf888dbb1a82632749cec31a";
constexpr const char* level015R05SourceManifest = "95416e1ca29191007c83a922f36f29932a33f67517f0a290a162537712cd2982";
constexpr const char* level015R06SourceManifest = "256fc2559125bc6f41e68aa0b5208c087725dcb2eb4f74166724749be913e4fd";
constexpr const char* level015R04SourceManifest = "cf16b8117349caaf3cfe5382b93d210871807386d13c260d0ebe5a81b1cec22d";
constexpr const char* level014R03Bundle = "46da261b872ba09db2cb0779464e75b2324eb34afadd7b86757ee753811f927c";
constexpr const char* l80Txt = "e2297c8404a4041af1289e095fcace5012e5079698b0d7c32ff1bf77808de8b6";
constexpr const char* l80Pdf = "cf99966ce9d5bd155d738dd30866a26fe0c30e2d633107393cf856bcb29c9afc";
constexpr const char* l80SourceManifest = "9774b44ab3c4fff7b21b0511e1b41b64f5d0ed8ce6116080a2b93776ab997e65";
constexpr const char* l26Txt = "816ef6a286175efe575ee93d14224aaaf44111af3ea58a73f6787898b478c0f5";
constexpr const char* l26Pdf = "c00d5751bb301d4a6b5bb66e009376218226fc90cb7f2d2fb0abbc2e0c9697d8";
constexpr const char* l26SourceManifest = "89da940807a1982b67550b25b2cb054f173c0fcf7bd122eb2589d5b47562987c";

struct Case {
    const char* item;
    const char* version;
    const char* bundle;
    std::int64_t revision;
    const char* txtHash;
    const char* txtReference;
    std::vector<std::string> refs;
    std::vector<std::string> variants;
};

const std::array<Case, 66> cases{{
    {"fg:item:000002", "representative-controls.1", originalBundle, 2, l3Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.txt#L3-TXT5-21,L3-TXT28-46",
     {"L3-TXT5-21", "L3-TXT28-46"},
     {"fg:variant:000006", "fg:variant:000008", "fg:variant:000010", "fg:variant:000012"}},
    {"fg:item:000003", "representative-controls.1", originalBundle, 2, l12Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt#L12-TXT14-28,L12-TXT34-52,L12-TXT34-53",
     {"L12-TXT14-28", "L12-TXT34-52", "L12-TXT34-53"},
     {"fg:variant:000029", "fg:variant:000030"}},
    {"fg:item:001141", "curriculum-v1-level012-rung02-local-build-only.1", rung02Bundle, 1, l12Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt#L12-TXT1-56-67",
     {"L12-TXT1-56-67", "L12-PDF1-p3", "L12-PDF1-p2", "L12-TXT1-1-40", "L12-TXT1-224-227", "L12-TXT1-229-231", "L12-PDF1-p1"},
     {"fg:variant:007404", "fg:variant:007405"}},
    {"fg:item:001142", "curriculum-v1-level012-rung03-local-build-only.1", rung03Bundle, 1, l12Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt#L12-TXT1-70-81",
     {"L12-TXT1-70-81", "L12-PDF1-p3", "L12-PDF1-p2", "L12-TXT1-1-40", "L12-TXT1-224-227", "L12-TXT1-229-231", "L12-PDF1-p1"},
     {"fg:variant:007406", "fg:variant:007407"}},
    {"fg:item:001143", "curriculum-v1-level012-rung04-local-build-only.2", rung04Bundle, 1, l12Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt#L12-TXT1-84-95",
     {"L12-TXT1-84-95", "L12-PDF1-p3", "L12-PDF1-p2", "L12-TXT1-1-40", "L12-TXT1-224-227", "L12-TXT1-229-231", "L12-PDF1-p1"},
     {"fg:variant:007408", "fg:variant:007409"}},
    {"fg:item:001144", "curriculum-v1-level006-ex001-first-cell-build-only.2", level006Bundle, 1, l6Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.txt#L6-TXT1-34-41",
     {"L6-TXT1-34-41", "L6-PDF1-p2", "L6-TXT1-1-23", "L6-PDF1-p1"},
     {"fg:variant:007410", "fg:variant:007411"}},
    {"fg:item:001145", "curriculum-v1-level012-rung05-local-build-only.1", rung05Bundle, 1, l12Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt#L12-TXT1-98-109",
     {"L12-TXT1-98-109", "L12-PDF1-p4", "L12-PDF1-p2", "L12-TXT1-1-40", "L12-TXT1-224-227", "L12-TXT1-229-231", "L12-PDF1-p1"},
     {"fg:variant:007412", "fg:variant:007413"}},
    {"fg:item:001146", "curriculum-v1-level008-ex001-first-shift-build-only.1", level008Bundle, 1, l8Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_8_Two_Position_Ladder.txt#L8-TXT1-31-38",
     {"L8-TXT1-31-38", "L8-PDF1-p2", "L8-TXT1-1-25", "L8-PDF1-p1"},
     {"fg:variant:007414", "fg:variant:007415"}},
    {"fg:item:001147", "curriculum-v1-level010-ex001-first-odd-shift-build-only.1", level010Bundle, 1, l10Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt#L10-TXT1-39-53",
     {"L10-TXT1-39-53", "L10-PDF1-p2", "L10-TXT1-1-33", "L10-PDF1-p1"},
     {"fg:variant:007416", "fg:variant:007417"}},
    {"fg:item:001148", "curriculum-v1-level007-ex001-relay-pass2-build-only.1", level007Bundle, 1, l7Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.txt#L7-TXT1-30-44",
     {"L7-TXT1-30-44", "L7-PDF1-p2", "L7-TXT1-1-24", "L7-PDF1-p1"},
     {"fg:variant:007418", "fg:variant:007419"}},
    {"fg:item:001149", "curriculum-v1-level009-ex001-first-up-down-pass2-build-only.1", level009Bundle, 1, l9Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt#L9-TXT1-31-45",
     {"L9-TXT1-31-45", "L9-PDF1-p2", "L9-TXT1-1-25", "L9-PDF1-p1"},
     {"fg:variant:007420", "fg:variant:007421"}},
    {"fg:item:001150", "curriculum-v1-level009-ex001-first-up-down-pass2-build-only.1", level009Bundle, 1, l9Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt#L9-TXT1-31-45",
     {"L9-TXT1-31-45", "L9-PDF1-p2", "L9-TXT1-1-25", "L9-PDF1-p1"},
     {"fg:variant:007422", "fg:variant:007423"}},
    {"fg:item:001151", "curriculum-v1-level011-ex001-first-up-down-pass2-build-only.1", level011Bundle, 1, l11Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_11_Three_Position_Relay.txt#L11-TXT1-51-57",
     {"L11-TXT1-51-57", "L11-PDF1-p2", "L11-TXT1-1-41", "L11-PDF1-p1"},
     {"fg:variant:007424", "fg:variant:007425"}},
    {"fg:item:001152", "curriculum-v1-level011-ex001-first-up-down-pass2-build-only.1", level011Bundle, 1, l11Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_11_Three_Position_Relay.txt#L11-TXT1-51-57",
     {"L11-TXT1-51-57", "L11-PDF1-p2", "L11-TXT1-1-41", "L11-PDF1-p1"},
     {"fg:variant:007426", "fg:variant:007427"}},
    {"fg:item:001153", "curriculum-v1-level013-rung01-a-and-a-bb-timed-build-only.1", level013Bundle, 1, l13Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.txt#L13-TXT-RULE-29-49,L13-TXT-RUNG01-52-63",
     {"L13-TXT-RULE-29-49", "L13-PDF-GUIDANCE-P1", "L13-TXT-RUNG01-52-63", "L13-TXT-RUNG02-66-77", "L13-PDF-CARDS-P3"},
     {"fg:variant:007428", "fg:variant:007429"}},
    {"fg:item:001154", "curriculum-v1-level013-rung01-a-and-a-bb-timed-build-only.1", level013Bundle, 1, l13Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.txt#L13-TXT-RULE-29-49,L13-TXT-RUNG01-52-63,L13-TXT-RUNG02-66-77",
     {"L13-TXT-RULE-29-49", "L13-PDF-GUIDANCE-P1", "L13-TXT-RUNG01-52-63", "L13-TXT-RUNG02-66-77", "L13-PDF-CARDS-P3"},
     {"fg:variant:007430", "fg:variant:007431"}},
    {"fg:item:001155", "curriculum-v1-level014-rung01-a-and-a-bb-triplet-build-only.1", level014Bundle, 1, l14Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L14-TXT-RULE-29-53,L14-TXT-RUNG01-56-67",
     {"L14-TXT-RULE-29-53", "L14-PDF-GUIDANCE-P1", "L14-TXT-RUNG01-56-67", "L14-TXT-RUNG02-70-81", "L14-PDF-CARDS-P3", "L14-PDF-ROUTE-P2"},
     {"fg:variant:007432", "fg:variant:007433"}},
    {"fg:item:001156", "curriculum-v1-level014-rung01-a-and-a-bb-triplet-build-only.1", level014Bundle, 1, l14Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L14-TXT-RULE-29-53,L14-TXT-RUNG01-56-67,L14-TXT-RUNG02-70-81",
     {"L14-TXT-RULE-29-53", "L14-PDF-GUIDANCE-P1", "L14-TXT-RUNG01-56-67", "L14-TXT-RUNG02-70-81", "L14-PDF-CARDS-P3", "L14-PDF-ROUTE-P2"},
     {"fg:variant:007434", "fg:variant:007435"}},
    {"fg:item:001157", "curriculum-v1-level015-rung01-complete-triplet-build-only.1", level015Bundle, 1, l15Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L15-TXT1-60-67,L15-TXT1-70-91",
     {"L15-TXT1-60-67", "L15-TXT1-70-91", "L15-PDF-GUIDANCE-P1", "L15-PDF-CARD-P3"},
     {"fg:variant:007436", "fg:variant:007437"}},
    {"fg:item:001181", "curriculum-v1-level015-rungs02-03-triplet-build-only.1", level015R0203Bundle, 1, l15Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L15-TXT1-60-67,L15-TXT1-94-115",
     {"L15-TXT1-60-67", "L15-TXT1-94-115", "L15-PDF-GUIDANCE-P1", "L15-PDF-ROUTE-P2", "L15-PDF-CARD-P3"},
     {"fg:variant:007702", "fg:variant:007703"}},
    {"fg:item:001182", "curriculum-v1-level015-rungs02-03-triplet-build-only.1", level015R0203Bundle, 1, l15Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L15-TXT1-60-67,L15-TXT1-118-139",
     {"L15-TXT1-60-67", "L15-TXT1-118-139", "L15-PDF-GUIDANCE-P1", "L15-PDF-ROUTE-P2", "L15-PDF-CARD-P4"},
     {"fg:variant:007704", "fg:variant:007705"}},
    {"fg:item:001158", "curriculum-v1-level016-first-two-cases-build-only.1", level016Bundle, 1, l16Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_16_Major_Scale_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L16-TXT-GUIDANCE,L16-TXT-RUNG01",
     {"L16-TXT-GUIDANCE", "L16-PDF-GUIDANCE", "L16-TXT-RUNG01", "L16-TXT-RUNG02", "L16-PDF-CARDS", "L16-PDF-ROUTE"},
     {"fg:variant:007438", "fg:variant:007439"}},
    {"fg:item:001159", "curriculum-v1-level016-first-two-cases-build-only.1", level016Bundle, 1, l16Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_16_Major_Scale_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L16-TXT-GUIDANCE,L16-TXT-RUNG01,L16-TXT-RUNG02",
     {"L16-TXT-GUIDANCE", "L16-PDF-GUIDANCE", "L16-TXT-RUNG01", "L16-TXT-RUNG02", "L16-PDF-CARDS", "L16-PDF-ROUTE"},
     {"fg:variant:007440", "fg:variant:007441"}},
    {"fg:item:001160", "curriculum-v1-level017-first-two-cases-build-only.1", level017Bundle, 1, l17Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L17-TXT-GUIDANCE,L17-TXT-RUNG01",
     {"L17-TXT-GUIDANCE", "L17-PDF-GUIDANCE", "L17-TXT-RUNG01", "L17-TXT-RUNG02", "L17-PDF-CARDS", "L17-PDF-ROUTE"},
     {"fg:variant:007442", "fg:variant:007443"}},
    {"fg:item:001161", "curriculum-v1-level017-first-two-cases-build-only.1", level017Bundle, 1, l17Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L17-TXT-GUIDANCE,L17-TXT-RUNG01,L17-TXT-RUNG02",
     {"L17-TXT-GUIDANCE", "L17-PDF-GUIDANCE", "L17-TXT-RUNG01", "L17-TXT-RUNG02", "L17-PDF-CARDS", "L17-PDF-ROUTE"},
     {"fg:variant:007444", "fg:variant:007445"}},
    {"fg:item:001162", "curriculum-v1-level018-first-two-cases-build-only.1", level018Bundle, 1, l18Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.txt#L18-TXT-GUIDANCE,L18-TXT-RUNG01",
     {"L18-TXT-GUIDANCE", "L18-PDF-GUIDANCE", "L18-TXT-RUNG01", "L18-TXT-RUNG02", "L18-PDF-CARDS", "L18-PDF-ROUTE"},
     {"fg:variant:007446", "fg:variant:007447"}},
    {"fg:item:001163", "curriculum-v1-level018-first-two-cases-build-only.1", level018Bundle, 1, l18Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.txt#L18-TXT-GUIDANCE,L18-TXT-RUNG01,L18-TXT-RUNG02",
     {"L18-TXT-GUIDANCE", "L18-PDF-GUIDANCE", "L18-TXT-RUNG01", "L18-TXT-RUNG02", "L18-PDF-CARDS", "L18-PDF-ROUTE"},
     {"fg:variant:007448", "fg:variant:007449"}},
    {"fg:item:001164", "curriculum-v1-level019-first-three-cases-build-only.1", level019Bundle, 1, l19Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_19_Major_Scale_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.txt#L19-TXT-GUIDANCE,L19-TXT-RUNG01",
     {"L19-TXT-GUIDANCE", "L19-PDF-GUIDANCE", "L19-TXT-RUNG01", "L19-TXT-RUNG02", "L19-TXT-RUNG03", "L19-PDF-CARDS01-02", "L19-PDF-CARD03", "L19-PDF-ROUTE"},
     {"fg:variant:007450", "fg:variant:007451"}},
    {"fg:item:001165", "curriculum-v1-level019-first-three-cases-build-only.1", level019Bundle, 1, l19Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_19_Major_Scale_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.txt#L19-TXT-GUIDANCE,L19-TXT-RUNG01,L19-TXT-RUNG02",
     {"L19-TXT-GUIDANCE", "L19-PDF-GUIDANCE", "L19-TXT-RUNG01", "L19-TXT-RUNG02", "L19-TXT-RUNG03", "L19-PDF-CARDS01-02", "L19-PDF-CARD03", "L19-PDF-ROUTE"},
     {"fg:variant:007452", "fg:variant:007453"}},
    {"fg:item:001166", "curriculum-v1-level019-first-three-cases-build-only.1", level019Bundle, 1, l19Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_19_Major_Scale_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.txt#L19-TXT-GUIDANCE,L19-TXT-RUNG01,L19-TXT-RUNG02,L19-TXT-RUNG03",
     {"L19-TXT-GUIDANCE", "L19-PDF-GUIDANCE", "L19-TXT-RUNG01", "L19-TXT-RUNG02", "L19-TXT-RUNG03", "L19-PDF-CARDS01-02", "L19-PDF-CARD03", "L19-PDF-ROUTE"},
     {"fg:variant:007454", "fg:variant:007455"}},
    {"fg:item:001167", "curriculum-v1-level020-a-full-circuit-build-only.1", level020Bundle, 1, l20Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_20_Major_Scale_Synthesis_Circuit_Two_Octave_Six_String_Neck_Ladder.txt#L20-TXT-GUIDANCE,L20-TXT-A-MODULE1,L20-TXT-A-MODULE2,L20-TXT-A-MODULE3,L20-TXT-A-MODULE4,L20-TXT-A-MODULE5",
     {"L20-TXT-GUIDANCE", "L20-PDF-PROTOCOL", "L20-PDF-ROUTE", "L20-TXT-A-MODULE1", "L20-TXT-A-MODULE2", "L20-TXT-A-MODULE3", "L20-TXT-A-MODULE4", "L20-TXT-A-MODULE5", "L20-PDF-A-MODULES1-3", "L20-PDF-A-MODULES4-5"},
     {"fg:variant:007456", "fg:variant:007457"}},
    {"fg:item:001168", "curriculum-v1-level021-first-three-cases-build-only.1", level021Bundle, 1, l21Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_21_Natural_Minor_One_Fret_Neck_Ladder.txt#L21-TXT-GUIDANCE,L21-TXT-RUNG01",
     {"L21-TXT-GUIDANCE", "L21-PDF-GUIDANCE", "L21-TXT-RUNG01", "L21-TXT-RUNG02", "L21-TXT-RUNG03", "L21-PDF-CARDS01-03", "L21-PDF-ROUTE"},
     {"fg:variant:007458", "fg:variant:007459"}},
    {"fg:item:001169", "curriculum-v1-level021-first-three-cases-build-only.1", level021Bundle, 1, l21Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_21_Natural_Minor_One_Fret_Neck_Ladder.txt#L21-TXT-GUIDANCE,L21-TXT-RUNG01,L21-TXT-RUNG02",
     {"L21-TXT-GUIDANCE", "L21-PDF-GUIDANCE", "L21-TXT-RUNG01", "L21-TXT-RUNG02", "L21-TXT-RUNG03", "L21-PDF-CARDS01-03", "L21-PDF-ROUTE"},
     {"fg:variant:007460", "fg:variant:007461"}},
    {"fg:item:001170", "curriculum-v1-level021-first-three-cases-build-only.1", level021Bundle, 1, l21Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_21_Natural_Minor_One_Fret_Neck_Ladder.txt#L21-TXT-GUIDANCE,L21-TXT-RUNG01,L21-TXT-RUNG02,L21-TXT-RUNG03",
     {"L21-TXT-GUIDANCE", "L21-PDF-GUIDANCE", "L21-TXT-RUNG01", "L21-TXT-RUNG02", "L21-TXT-RUNG03", "L21-PDF-CARDS01-03", "L21-PDF-ROUTE"},
     {"fg:variant:007462", "fg:variant:007463"}},
    {"fg:item:001171", "curriculum-v1-level022-first-neighbor-pair-build-only.1", level022Bundle, 1, l22Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_22_Natural_Minor_Two_Octave_Six_String_Neck_Ladder.txt#L22-TXT-GUIDANCE,L22-TXT-RUNG01,L22-TXT-RUNG02",
     {"L22-TXT-GUIDANCE", "L22-PDF-GUIDANCE", "L22-PDF-ROUTE", "L22-TXT-RUNG01", "L22-TXT-RUNG02", "L22-PDF-CARDS01-02"},
     {"fg:variant:007464", "fg:variant:007465"}},
    {"fg:item:001172", "curriculum-v1-level023-first-rolling-cell-build-only.1", level023Bundle, 1, l23Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_23_Natural_Minor_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L23-TXT-RULE-1-60,L23-TXT-RUNG01-62-73",
     {"L23-TXT-RULE-1-60", "L23-PDF-GUIDANCE-P1", "L23-TXT-RUNG01-62-73", "L23-PDF-CARD01-P3"},
     {"fg:variant:007466", "fg:variant:007467"}},
    {"fg:item:001173", "curriculum-v1-level024-first-linked-cell-build-only.1", level024Bundle, 1, l24Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_24_Natural_Minor_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L24-TXT-RULE-1-70,L24-TXT-RUNG01-73-94",
     {"L24-TXT-RULE-1-70", "L24-TXT-RUNG01-73-94", "L24-PDF-TUNING-P2", "L24-PDF-CARD01-P3", "L24-PDF-PHASES-P10"},
     {"fg:variant:007468", "fg:variant:007469"}},
    {"fg:item:001174", "curriculum-v1-level030-first12-build-only.1", level030Bundle, 1, l30Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_IV_Level_30_Major_Pentatonic_One_Octave_One_Fret_Neck_Ladder.txt#L30-TXT-RULE-14-30,L30-TXT-PRACTICE-40-46,L30-TXT-RUNG01-49-60",
     {"L30-TXT-RULE-14-30", "L30-TXT-PRACTICE-40-46", "L30-TXT-RUNG01-49-60", "L30-PDF-P1", "L30-PDF-P2"},
     {"fg:variant:007470", "fg:variant:007471"}},
    {"fg:item:001175", "curriculum-v1-level029-module1-first30-build-only.1", level029Bundle, 1, l29Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_29_Natural_Minor_Synthesis_Circuit_Two_Octave_Six_String_Neck_Ladder.txt#L29-TXT-RULES-1-46,L29-TXT-RUNG01-80-95",
     {"L29-TXT-RULES-1-46", "L29-TXT-RUNG01-80-95", "L29-PDF-PULSE-P2", "L29-PDF-CARD-P3"},
     {"fg:variant:007472", "fg:variant:007473"}},
    {"fg:item:001176", "curriculum-v1-level025-first-cell-build-only.1", level025Bundle, 1, l25Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_25_Natural_Minor_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L25-TXT-RULE-1-64,L25-TXT-RUNG01-67-78",
     {"L25-TXT-RULE-1-64", "L25-TXT-RUNG01-67-78", "L25-PDF-WORKED-P1", "L25-PDF-CARD01-P3"},
     {"fg:variant:007474", "fg:variant:007475"}},
    {"fg:item:001177", "curriculum-v1-level026-first-cell-build-only.1", level026Bundle, 1, l26Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_III_Level_26_Natural_Minor_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L26-TXT-RULE-1-76,L26-TXT-RUNG01-79-100",
     {"L26-TXT-RULE-1-76", "L26-TXT-RUNG01-79-100", "L26-PDF-CARD01-P3"},
     {"fg:variant:007476", "fg:variant:007477"}},
    {"fg:item:001178", "curriculum-v1-level012-rung08-first-cell-build-only.1", level012R08Bundle, 1, l12Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.txt#L12-TXT1-140-151",
     {"L12-TXT1-140-151", "L12-PDF1-p4", "L12-PDF1-p2", "L12-TXT1-1-40", "L12-TXT1-224-227", "L12-TXT1-229-231", "L12-PDF1-p1"},
     {"fg:variant:007694", "fg:variant:007695"}},
    {"fg:item:001179", "curriculum-v1-level080-module-a-pass1-r02-supplemental-build-only.1", level080R02Bundle, 1, l80Txt,
     "Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_80_Chord_Melody_Independent_Voice_Control_Bass_Melody_Inner_Guide_Tones_and_Simultaneous_Accompaniment_Lead.txt#L080-TXT-MODULE-A-L26-27",
     {"L080-TXT-MODULE-A-L26-27", "L080-PDF-P3-MODULE-A", "GV-L080-MA-PASS1-AUTHORED"},
     {"fg:variant:007696"}},
    {"fg:item:001130", "curriculum-v1-level013-rung03-neighboring-cell-build-only.1", level013R03Bundle, 1, l13Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.txt#L13-TXT1-80-91",
     {"L13-TXT1-80-91", "L13-PDF1-p3", "L13-TXT1-30-49", "L13-PDF1-p2", "L13-TXT1-234-239"},
     {"fg:variant:007382", "fg:variant:007383"}},
    {"fg:item:001183", "curriculum-v1-level013-rung04-neighboring-cell-build-only.1", level013R04Bundle, 1, l13Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.txt#L13-TXT1-94-105",
     {"L13-TXT1-94-105", "L13-PDF1-p4", "L13-TXT1-30-49", "L13-PDF1-p2", "L13-TXT1-234-239"},
     {"fg:variant:007706", "fg:variant:007707"}},
    {"fg:item:001184", "curriculum-v1-level013-rung05-neighboring-cell-build-only.1", level013R05Bundle, 1, l13Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.txt#L13-TXT1-108-119",
     {"L13-TXT1-108-119", "L13-PDF1-p4", "L13-TXT1-30-49", "L13-PDF1-p2", "L13-TXT1-234-239"},
     {"fg:variant:007708", "fg:variant:007709"}},
    {"fg:item:001185", "curriculum-v1-level015-rung05-triplet-build-only.1", level015R05Bundle, 1, l15Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L15-TXT1-166-187",
     {"L15-TXT1-34-47", "L15-TXT1-59-67", "L15-TXT1-166-187", "L15-PDF-GUIDANCE-P1", "L15-PDF-CARD-P5"},
     {"fg:variant:007710", "fg:variant:007711"}},
    {"fg:item:001186", "curriculum-v1-level015-rung04-triplet-build-only.1", level015R04Bundle, 1, l15Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L15-TXT1-142-163",
     {"L15-TXT1-34-47", "L15-TXT1-59-67", "L15-TXT1-142-163", "L15-PDF-GUIDANCE-P1", "L15-PDF-CARD-P4"},
     {"fg:variant:007712", "fg:variant:007713"}},
    {"fg:item:001187", "curriculum-v1-level015-rung06-triplet-build-only.1", level015R06Bundle, 1, l15Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt#L15-TXT1-190-211",
     {"L15-TXT1-34-47", "L15-TXT1-59-67", "L15-TXT1-190-211", "L15-PDF-GUIDANCE-P1", "L15-PDF-CARD-P5"},
     {"fg:variant:007714", "fg:variant:007715"}},
    {"fg:item:001188", "curriculum-v1-level002-ex002-1213-straight16-private.1", level002Ex002Bundle, 1, level002Ex002Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_2_Two_String_Transfer.txt#L2-TXT34-48",
     {"L2-TXT1-12", "L2-PDF1", "L2-TXT15-15", "L2-TXT34-48"},
     {"fg:variant:007716", "fg:variant:007717"}},
    {"fg:item:000240", "level003-modeb001-ex001-rev1-reference.1", level003ModeB001Bundle, 1, l3Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.txt#L3-TXT229-243",
     {"L3-TXT1-21", "L3-PDF1", "L3-TXT24-24", "L3-TXT225-226", "L3-TXT229-243"},
     {"fg:variant:000827", "fg:variant:000829"}},
    {"fg:item:000445", "level004-ex002-rev1-reference.1", level004Ex002Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT44-58",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT44-58"},
     {"fg:variant:003287", "fg:variant:003289"}},
    {"fg:item:000446", "level004-ex003-rev1-reference.1", level004Ex003Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT60-74",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT60-74"},
     {"fg:variant:003299", "fg:variant:003301"}},
    {"fg:item:000447", "level004-ex004-rev1-reference.1", level004Ex004Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT76-90",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT76-90"},
     {"fg:variant:003311", "fg:variant:003313"}},
    {"fg:item:000448", "level004-ex004-rev1-reference.1", level004Ex005Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT92-106",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT92-106"},
     {"fg:variant:003323", "fg:variant:003325"}},
    {"fg:item:000449", "level004-ex006-rev1-reference.1", level004Ex006Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT108-122",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT108-122"},
     {"fg:variant:003335", "fg:variant:003337"}},
    {"fg:item:000450", "level004-ex007-rev1-reference.1", level004Ex007Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT124-138",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT124-138"},
     {"fg:variant:003347", "fg:variant:003349"}},
    {"fg:item:000451", "level004-ex008-rev1-reference.1", level004Ex008Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT140-154",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT140-154"},
     {"fg:variant:003359", "fg:variant:003361"}},
    {"fg:item:000452", "level004-ex009-rev1-reference.1", level004Ex009Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT156-170",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT156-170"},
     {"fg:variant:003371", "fg:variant:003373"}},
    {"fg:item:000453", "level004-ex010-rev1-reference.1", level004Ex010Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT172-186",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT172-186"},
     {"fg:variant:003383", "fg:variant:003385"}},
    {"fg:item:000454", "level004-ex011-rev1-reference.1", level004Ex011Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT188-202",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT188-202"},
     {"fg:variant:003395", "fg:variant:003397"}},
    {"fg:item:000455", "level004-ex012-rev1-reference.1", level004Ex012Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT204-218",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT25-25", "L4-TXT204-218"},
     {"fg:variant:003407", "fg:variant:003409"}},
    {"fg:item:000456", "level004-ex013-rev1-reference.1", level004Ex013Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT224-238",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT221-221", "L4-TXT224-238"},
     {"fg:variant:003419", "fg:variant:003421"}},
    {"fg:item:000457", "level004-ex014-rev1-reference.1", level004Ex014Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT240-254",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT221-221", "L4-TXT240-254"},
     {"fg:variant:003431", "fg:variant:003433"}},
    {"fg:item:000458", "level004-ex015-rev1-reference.1", level004Ex015Bundle, 1, l4Txt,
     "Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt#L4-TXT256-270",
     {"L4-TXT1-22", "L4-PDF1", "L4-TXT221-221", "L4-TXT256-270"},
     {"fg:variant:003443", "fg:variant:003445"}},
    {"fg:item:001180", "curriculum-v1-level014-rung03-triplet-build-only.1", level014R03Bundle, 1, l14Txt,
     "Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt#L14-TXT1-84-95",
     {"L14-TXT1-84-95", "L14-PDF1-p3", "L14-PDF1-p2", "L14-PDF1-p1", "L14-TXT1-5-8", "L14-TXT1-16-17", "L14-TXT1-24-27", "L14-TXT1-30-33", "L14-TXT1-36-41", "L14-TXT1-44-45", "L14-TXT1-48-53", "L14-TXT1-239-241", "L14-TXT1-244-246"},
     {"fg:variant:007698", "fg:variant:007699"}},
}};

const json::Value& field(const json::Value& value, const char* key) {
    const auto* found = value.find(key);
    if (!found) throw DomainCoverageError(std::string("Installed admission lacks ") + key);
    return *found;
}
std::string stringField(const json::Value& value, const char* key) {
    const auto& found = field(value, key);
    if (!found.isString()) throw DomainCoverageError(std::string("Invalid installed admission ") + key);
    return found.string();
}
std::vector<std::string> refs(const json::Value& value) {
    if (!value.isArray()) throw DomainCoverageError("Invalid installed source refs");
    std::vector<std::string> result;
    for (const auto& ref : value.array()) {
        if (!ref.isString()) throw DomainCoverageError("Invalid installed source ref");
        result.push_back(ref.string());
    }
    return result;
}
void require(bool good, const char* reason) {
    if (!good) throw DomainCoverageError(reason);
}
} // namespace

std::vector<std::string> installedDomainManifests() {
    return {originalBundle, rung02Bundle, rung03Bundle, rung04Bundle, level006Bundle, rung05Bundle, level008Bundle, level010Bundle, level007Bundle, level009Bundle, level011Bundle, level013Bundle, level014Bundle, level015Bundle, level016Bundle, level017Bundle, level018Bundle, level019Bundle, level020Bundle, level021Bundle, level022Bundle, level023Bundle, level024Bundle, level030Bundle, level029Bundle, level025Bundle, level026Bundle, level012R08Bundle, level080R02Bundle, level013R03Bundle, level014R03Bundle, level015R0203Bundle, level001Bundle, level013R04Bundle, level013R05Bundle, level015R05Bundle, level015R04Bundle, level015R06Bundle, level002Ex002Bundle, level003ModeB001Bundle, level004Ex002Bundle, level004Ex003Bundle, level004Ex004Bundle, level004Ex005Bundle, level004Ex006Bundle, level004Ex007Bundle, level004Ex008Bundle, level004Ex009Bundle, level004Ex010Bundle, level004Ex011Bundle, level004Ex012Bundle, level004Ex013Bundle, level004Ex014Bundle, level004Ex015Bundle};
}

MultiDomainCatalog installedDomainCatalog(const lesson::Catalog& installed) {
    MultiDomainCatalog result;
    result.version = "p02-installed-practice-domain-current.44";
    for (const auto& manifest : installedDomainManifests()) {
        DomainCatalog member;
        member.version = result.version;
        member.contentManifestSha256 = manifest;
        member.sourceManifestSha256 = manifest == level001Bundle ? level001SourceManifest : (manifest == level080R02Bundle ? l80SourceManifest : (manifest == level026Bundle ? l26SourceManifest : manifest == level025Bundle ? l25SourceManifest : (manifest == level029Bundle ? l29SourceManifest : (manifest == level030Bundle ? l30SourceManifest : (manifest == level024Bundle ? l24SourceManifest : sourceManifest)))));
        if (manifest == level015R05Bundle) member.sourceManifestSha256 = level015R05SourceManifest;
        if (manifest == level015R04Bundle) member.sourceManifestSha256 = level015R04SourceManifest;
        if (manifest == level015R06Bundle) member.sourceManifestSha256 = level015R06SourceManifest;
        if (manifest == level002Ex002Bundle) member.sourceManifestSha256 = level002Ex002SourceManifest;
        if (manifest == level003ModeB001Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex002Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex003Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex004Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex005Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex006Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex007Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex008Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex009Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex010Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex011Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex012Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex013Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex014Bundle) member.sourceManifestSha256 = sourceManifest;
        if (manifest == level004Ex015Bundle) member.sourceManifestSha256 = sourceManifest;
        result.catalogs.push_back(std::move(member));
    }
    for (const auto& selected : cases) {
        const char* selectedSourceManifest = std::string(selected.item) == "fg:item:001179" ? l80SourceManifest : (std::string(selected.item) == "fg:item:001177" ? l26SourceManifest : std::string(selected.item) == "fg:item:001176" ? l25SourceManifest : (std::string(selected.item) == "fg:item:001175" ? l29SourceManifest : (std::string(selected.item) == "fg:item:001174" ? l30SourceManifest : (std::string(selected.item) == "fg:item:001173" ? l24SourceManifest : sourceManifest))));
        if (std::string(selected.item) == "fg:item:001185") selectedSourceManifest = level015R05SourceManifest;
        if (std::string(selected.item) == "fg:item:001186") selectedSourceManifest = level015R04SourceManifest;
        if (std::string(selected.item) == "fg:item:001187") selectedSourceManifest = level015R06SourceManifest;
        if (std::string(selected.item) == "fg:item:001188") selectedSourceManifest = level002Ex002SourceManifest;
        if (std::string(selected.item) == "fg:item:000240") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000445") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000446") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000447") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000448") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000449") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000450") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000451") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000452") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000453") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000454") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000455") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000456") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000457") selectedSourceManifest = sourceManifest;
        if (std::string(selected.item) == "fg:item:000458") selectedSourceManifest = sourceManifest;
        auto& member = *std::find_if(result.catalogs.begin(), result.catalogs.end(),
            [&](const DomainCatalog& value) { return value.contentManifestSha256 == selected.bundle; });
        for (const auto& variant : selected.variants) {
            const auto admission = installed.admit(selected.item, variant);
            require(admission && admission->practiceAllowed(), "Selected case is not Practice admitted");
            const auto& identity = admission->identity();
            std::int64_t revision{};
            require(field(identity, "content_revision").integer(revision) && revision == selected.revision,
                    "Installed content revision changed");
            require(stringField(identity, "bundle_sha256") == selected.bundle
                    && stringField(identity, "item_id") == selected.item
                    && stringField(identity, "variant_id") == variant
                    && stringField(identity, "content_version") == selected.version
                    && stringField(identity, "source_manifest_sha256") == selectedSourceManifest,
                    "Installed bundle, version or source identity changed");
            require(refs(field(identity, "source_refs")) == selected.refs,
                    "Installed source references changed");
            const auto& hashes = field(identity, "source_hashes");
            require(hashes.isObject() && stringField(hashes, selected.refs.front().c_str()) == selected.txtHash,
                    "Installed source TXT provenance changed");
            if (std::string(selected.item) == "fg:item:001146")
                require(stringField(hashes, "L8-PDF1-p2") == l8Pdf
                        && stringField(hashes, "L8-PDF1-p1") == l8Pdf,
                        "Installed Level8 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001147")
                require(stringField(hashes, "L10-PDF1-p2") == l10Pdf
                        && stringField(hashes, "L10-PDF1-p1") == l10Pdf,
                        "Installed Level10 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001148")
                require(stringField(hashes, "L7-PDF1-p2") == l7Pdf
                        && stringField(hashes, "L7-PDF1-p1") == l7Pdf,
                        "Installed Level7 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001149"
                    || std::string(selected.item) == "fg:item:001150")
                require(stringField(hashes, "L9-PDF1-p2") == l9Pdf
                        && stringField(hashes, "L9-PDF1-p1") == l9Pdf,
                        "Installed Level9 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001151"
                    || std::string(selected.item) == "fg:item:001152")
                require(stringField(hashes, "L11-PDF1-p2") == l11Pdf
                        && stringField(hashes, "L11-PDF1-p1") == l11Pdf,
                        "Installed Level11 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001153"
                    || std::string(selected.item) == "fg:item:001154")
                require(stringField(hashes, "L13-PDF-GUIDANCE-P1") == l13Pdf
                        && stringField(hashes, "L13-PDF-CARDS-P3") == l13Pdf,
                        "Installed Level13 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001155"
                    || std::string(selected.item) == "fg:item:001156")
                require(stringField(hashes, "L14-PDF-GUIDANCE-P1") == l14Pdf
                        && stringField(hashes, "L14-PDF-CARDS-P3") == l14Pdf
                        && stringField(hashes, "L14-PDF-ROUTE-P2") == l14Pdf,
                        "Installed Level14 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001180")
                require(stringField(hashes, "L14-PDF1-p1") == l14Pdf
                        && stringField(hashes, "L14-PDF1-p2") == l14Pdf
                        && stringField(hashes, "L14-PDF1-p3") == l14Pdf,
                        "Installed Level14 Rung03 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001157")
                require(stringField(hashes, "L15-PDF-GUIDANCE-P1") == l15Pdf
                        && stringField(hashes, "L15-PDF-CARD-P3") == l15Pdf,
                        "Installed Level15 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001181" || std::string(selected.item) == "fg:item:001182")
                require(stringField(hashes, "L15-PDF-GUIDANCE-P1") == l15Pdf &&
                        stringField(hashes, "L15-PDF-ROUTE-P2") == l15Pdf &&
                        stringField(hashes, std::string(selected.item) == "fg:item:001181" ? "L15-PDF-CARD-P3" : "L15-PDF-CARD-P4") == l15Pdf,
                        "Installed Level15 Rungs02-03 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001158"
                    || std::string(selected.item) == "fg:item:001159")
                require(stringField(hashes, "L16-PDF-GUIDANCE") == l16Pdf
                        && stringField(hashes, "L16-PDF-CARDS") == l16Pdf
                        && stringField(hashes, "L16-PDF-ROUTE") == l16Pdf,
                        "Installed Level16 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001160"
                    || std::string(selected.item) == "fg:item:001161")
                require(stringField(hashes, "L17-PDF-GUIDANCE") == l17Pdf
                        && stringField(hashes, "L17-PDF-CARDS") == l17Pdf
                        && stringField(hashes, "L17-PDF-ROUTE") == l17Pdf,
                        "Installed Level17 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001162"
                    || std::string(selected.item) == "fg:item:001163")
                require(stringField(hashes, "L18-PDF-GUIDANCE") == l18Pdf
                        && stringField(hashes, "L18-PDF-CARDS") == l18Pdf
                        && stringField(hashes, "L18-PDF-ROUTE") == l18Pdf,
                        "Installed Level18 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001164"
                    || std::string(selected.item) == "fg:item:001165"
                    || std::string(selected.item) == "fg:item:001166")
                require(stringField(hashes, "L19-PDF-GUIDANCE") == l19Pdf
                        && stringField(hashes, "L19-PDF-CARDS01-02") == l19Pdf
                        && stringField(hashes, "L19-PDF-CARD03") == l19Pdf
                        && stringField(hashes, "L19-PDF-ROUTE") == l19Pdf,
                        "Installed Level19 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001168"
                    || std::string(selected.item) == "fg:item:001169"
                    || std::string(selected.item) == "fg:item:001170")
                require(stringField(hashes, "L21-PDF-GUIDANCE") == l21Pdf
                        && stringField(hashes, "L21-PDF-CARDS01-03") == l21Pdf
                        && stringField(hashes, "L21-PDF-ROUTE") == l21Pdf,
                        "Installed Level21 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001171")
                require(stringField(hashes, "L22-PDF-GUIDANCE") == l22Pdf
                        && stringField(hashes, "L22-PDF-ROUTE") == l22Pdf
                        && stringField(hashes, "L22-PDF-CARDS01-02") == l22Pdf,
                        "Installed Level22 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001172")
                require(stringField(hashes, "L23-PDF-GUIDANCE-P1") == l23Pdf
                        && stringField(hashes, "L23-PDF-CARD01-P3") == l23Pdf,
                        "Installed Level23 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001173")
                require(stringField(hashes, "L24-PDF-TUNING-P2") == l24Pdf
                        && stringField(hashes, "L24-PDF-CARD01-P3") == l24Pdf
                        && stringField(hashes, "L24-PDF-PHASES-P10") == l24Pdf,
                        "Installed Level24 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001174")
                require(stringField(hashes, "L30-PDF-P1") == l30Pdf
                        && stringField(hashes, "L30-PDF-P2") == l30Pdf,
                        "Installed Level30 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001175")
                require(stringField(hashes, "L29-PDF-PULSE-P2") == l29Pdf
                        && stringField(hashes, "L29-PDF-CARD-P3") == l29Pdf,
                        "Installed Level29 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001176")
                require(stringField(hashes, "L25-PDF-WORKED-P1") == l25Pdf
                        && stringField(hashes, "L25-PDF-CARD01-P3") == l25Pdf,
                        "Installed Level25 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001177")
                require(stringField(hashes, "L26-PDF-CARD01-P3") == l26Pdf,
                        "Installed Level26 source PDF provenance changed");
            if (std::string(selected.item) == "fg:item:001179")
                require(stringField(hashes, "L080-PDF-P3-MODULE-A") == l80Pdf &&
                        stringField(hashes, "GV-L080-MA-PASS1-AUTHORED") == "11701831a73e5fca67e4fe53c38aa1e521812f79b912b3bdfeb22cd215d329a2",
                        "Installed Level80 printed and authored source provenance changed");
            DomainMetadata entry;
            entry.binding = {selected.item, variant, selected.version, selectedSourceManifest,
                selected.revision, selected.refs};
            entry.domains = {"Technique/fretboard"};
            entry.provenanceReference = selected.txtReference;
            entry.provenanceSha256 = selected.txtHash;
            if (std::string(selected.item) == "fg:item:000240") {
                require(stringField(hashes, "L3-PDF1") == l3Pdf,"Installed Level3 ModeB001 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000445") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise002 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000446") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise003 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000447") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise004 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000448") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise005 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000449") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise006 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000450") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise007 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000451") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise008 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000452") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise009 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000453") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise010 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000454") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise011 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000455") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise012 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000456") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise013 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000457") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise014 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000458") {
                require(stringField(hashes, "L4-PDF1") == l4Pdf,"Installed Level4 Exercise015 PDF provenance changed");
            }
            if (std::string(selected.item) == "fg:item:000240") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.pdf#page3";
                entry.supportingSha256 = l3Pdf;
            } else if (std::string(selected.item) == "fg:item:000445") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000446") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000447") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000448") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000449") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000450") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000451") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000452") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000453") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000454") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000455") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page2";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000456") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page3";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000457") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page3";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000458") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf#page3";
                entry.supportingSha256 = l4Pdf;
            } else if (std::string(selected.item) == "fg:item:000002") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.pdf#pages1-2";
                entry.supportingSha256 = l3Pdf;
            } else if (std::string(selected.item) == "fg:item:001144") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer.pdf#pages1-2";
                entry.supportingSha256 = l6Pdf;
            } else if (std::string(selected.item) == "fg:item:001146") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_8_Two_Position_Ladder.pdf#pages1-2";
                entry.supportingSha256 = l8Pdf;
            } else if (std::string(selected.item) == "fg:item:001147") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf#pages1-2";
                entry.supportingSha256 = l10Pdf;
            } else if (std::string(selected.item) == "fg:item:001148") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_7_Three_String_Skip_Relay.pdf#pages1-2";
                entry.supportingSha256 = l7Pdf;
            } else if (std::string(selected.item) == "fg:item:001149"
                    || std::string(selected.item) == "fg:item:001150") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf#pages1-2";
                entry.supportingSha256 = l9Pdf;
            } else if (std::string(selected.item) == "fg:item:001151"
                    || std::string(selected.item) == "fg:item:001152") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_11_Three_Position_Relay.pdf#pages1-2";
                entry.supportingSha256 = l11Pdf;
            } else if (std::string(selected.item) == "fg:item:001153"
                    || std::string(selected.item) == "fg:item:001154") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l13Pdf;
            } else if (std::string(selected.item) == "fg:item:001155"
                    || std::string(selected.item) == "fg:item:001156") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l14Pdf;
            } else if (std::string(selected.item) == "fg:item:001180") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l14Pdf;
            } else if (std::string(selected.item) == "fg:item:001157") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf#pages1,3";
                entry.supportingSha256 = l15Pdf;
            } else if (std::string(selected.item) == "fg:item:001158"
                    || std::string(selected.item) == "fg:item:001159") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_16_Major_Scale_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf#pages1,3";
                entry.supportingSha256 = l16Pdf;
            } else if (std::string(selected.item) == "fg:item:001160"
                    || std::string(selected.item) == "fg:item:001161") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l17Pdf;
            } else if (std::string(selected.item) == "fg:item:001162"
                    || std::string(selected.item) == "fg:item:001163") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l18Pdf;
            } else if (std::string(selected.item) == "fg:item:001164"
                    || std::string(selected.item) == "fg:item:001165"
                    || std::string(selected.item) == "fg:item:001166") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_19_Major_Scale_Diatonic_Triads_Two_Octave_Six_String_Neck_Ladder.pdf#pages1-4";
                entry.supportingSha256 = l19Pdf;
            } else if (std::string(selected.item) == "fg:item:001168"
                    || std::string(selected.item) == "fg:item:001169"
                    || std::string(selected.item) == "fg:item:001170") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_21_Natural_Minor_One_Fret_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l21Pdf;
            } else if (std::string(selected.item) == "fg:item:001171") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_22_Natural_Minor_Two_Octave_Six_String_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l22Pdf;
            } else if (std::string(selected.item) == "fg:item:001172") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_23_Natural_Minor_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf#pages1,3";
                entry.supportingSha256 = l23Pdf;
            } else if (std::string(selected.item) == "fg:item:001173") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_24_Natural_Minor_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf#pages2,3,10";
                entry.supportingSha256 = l24Pdf;
            } else if (std::string(selected.item) == "fg:item:001174") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_IV_Level_30_Major_Pentatonic_One_Octave_One_Fret_Neck_Ladder.pdf#pages1-2";
                entry.supportingSha256 = l30Pdf;
            } else if (std::string(selected.item) == "fg:item:001175") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_29_Natural_Minor_Synthesis_Circuit_Two_Octave_Six_String_Neck_Ladder.pdf#pages2-3";
                entry.supportingSha256 = l29Pdf;
            } else if (std::string(selected.item) == "fg:item:001176") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_25_Natural_Minor_Four_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf#pages1,3";
                entry.supportingSha256 = l25Pdf;
            } else if (std::string(selected.item) == "fg:item:001177") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_III_Level_26_Natural_Minor_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf#page3";
                entry.supportingSha256 = l26Pdf;
            } else if (std::string(selected.item) == "fg:item:001179") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_80_Chord_Melody_Independent_Voice_Control_Bass_Melody_Inner_Guide_Tones_and_Simultaneous_Accompaniment_Lead.pdf#page3";
                entry.supportingSha256 = l80Pdf;
            } else if (std::string(selected.item) == "fg:item:001188") {
                entry.supportingReference = "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_2_Two_String_Transfer.pdf#pages1-2";
                entry.supportingSha256 = "cfcc4b3414400f5bfc2510c30c407f0d72e573ef8e899a184820202d67671ac8";
            } else {
                entry.supportingReference = "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_12_Major_Scale_One_Fret_Neck_Ladder.pdf#pages1-3";
                entry.supportingSha256 = l12Pdf;
            }
            entry.vocabularyReference = "Source/progression/SourceRubrics.json#Technique/fretboard";
            entry.vocabularySha256 = vocabularySha;
            member.entries.push_back(std::move(entry));
        }
    }
    // Full Level1 has 108 reviewed source units and only the two new full48
    // selections per item are Practice-admitted. The 432 historical half routes
    // remain visible in Learn but receive no recorded domain permission.
    const auto level001It=std::find_if(result.catalogs.begin(),result.catalogs.end(),
        [](const auto& member){return member.contentManifestSha256==level001Bundle;});
    require(level001It!=result.catalogs.end(),"Level1 domain owner missing");
    auto& level001Member=*level001It;
    require(level001Member.contentManifestSha256==level001Bundle&&
        level001Member.sourceManifestSha256==level001SourceManifest,"Level1 domain owner differs");
    require(installed.lessons().size()==184,"Finite Level1 installed case count differs");
    const auto fullId=[](std::size_t n){const auto digits=std::to_string(n);
        return "fg:variant:"+std::string(6-digits.size(),'0')+digits;};
    const auto addLevel001=[&](const lesson::Lesson& selected,std::size_t ordinal){
        const std::string item=selected.id;
        require(selected.level==1&&selected.variants.size()==6&&
            selected.variants[4].id==fullId(7478+2*(ordinal-1))&&
            selected.variants[5].id==fullId(7479+2*(ordinal-1)),
            "Level1 selected case or D/U identity differs");
        for(std::size_t choice=4;choice<6;++choice){
            const std::string variant=selected.variants[choice].id;
            const auto admission=installed.admit(item,variant);
            require(admission&&admission->practiceAllowed(),"Level1 full48 Practice admission missing");
            const auto& identity=admission->identity();
            std::int64_t revision{};
            require(field(identity,"content_revision").integer(revision)&&
                revision==(ordinal==1?4:2)&&
                stringField(identity,"item_id")==item&&
                stringField(identity,"variant_id")==variant&&
                stringField(identity,"bundle_sha256")==level001Bundle&&
                stringField(identity,"source_manifest_sha256")==level001SourceManifest&&
                stringField(identity,"content_version")=="level001-full-route-quarter-pulse-108-candidate.1",
                "Level1 recorded identity/version differs");
            const auto sourceRefs=refs(field(identity,"source_refs"));
            require(!sourceRefs.empty(),"Level1 source references missing");
            const auto& hashes=field(identity,"source_hashes");
            require(hashes.isObject()&&stringField(hashes,sourceRefs.front().c_str())==level001Txt&&
                stringField(hashes,"L1-FATHOM-FULL48-QUARTER-PULSE")==
                    "8d1e053294d143ccd73bcfcf11cd9597ec3b7e2673555ee864d3ae9b00c19ec0",
                "Level1 printed TXT or authored timing provenance differs");
            DomainMetadata entry;
            entry.binding={item,variant,"level001-full-route-quarter-pulse-108-candidate.1",
                level001SourceManifest,revision,sourceRefs};
            entry.domains={"Technique/fretboard"};
            entry.provenanceReference=std::string("Notes/music/guitar project/TXT version/108_Finger_Permutations_Guitar_Tablature.txt#")+sourceRefs.front();
            entry.provenanceSha256=level001Txt;
            entry.supportingReference="Notes/music/guitar project/PDF version/108_Finger_Permutations_Guitar_Tablature.pdf#pages1-4";
            entry.supportingSha256=level001Pdf;
            entry.vocabularyReference="Source/progression/SourceRubrics.json#Technique/fretboard";
            entry.vocabularySha256=vocabularySha;
            level001Member.entries.push_back(std::move(entry));
        }
    };
    for(std::size_t i=0;i<108;++i)addLevel001(installed.lessons()[55+i],i+1);
    require(level001Member.entries.size()==216,"Level1 recorded domain coverage differs");
    return result;
}
} // namespace fathom::progression
