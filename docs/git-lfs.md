# Git LFS: the large runtime definition file

The full source uses one Git LFS path, narrowly declared in `.gitattributes`:

```gitattributes
/RuntimeAssets/compiled-recipe-families-v1/manual-procedure-graph/definitions.jsonl filter=lfs diff=lfs merge=lfs -text
```

The hydrated file is 137,376,520 bytes with SHA-256 `258cad9248a47c3dd14dcd5a369293b8c071e3db7cf84ff12f734d14e27ff4c1`. Ordinary GitHub Git objects are limited to 100 MiB; [GitHub documents the limit and LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). Only this path is LFS-tracked. The 60,064,866-byte generated manual-graph header remains ordinary Git data and exceeds GitHub's warning threshold, not its hard file limit.

The supplied local folder already contains the full verified file. **It builds without fetching anything.** LFS pointers are Git index/storage representations; they must not replace the runtime working bytes. The runtime transport and file manifests still hash the hydrated content. A pointer in the working tree is not usable curriculum and fails integrity checks.

## Future authorized clone

Prerequisites: Git and Git LFS installed by the developer, plus the build requirements in [development](development.md). Git LFS 3.7.1 was already installed and verified locally for this preparation. This documentation does not install software or accept terms.

Only after a repository exists and its owner authorizes access, set `FATHOM_REPOSITORY_URL` to that actual URL. No repository URL is invented here. These are future network commands, not actions performed during local preparation:

```sh
GIT_LFS_SKIP_SMUDGE=1 git clone "$FATHOM_REPOSITORY_URL" Fathom
cd Fathom
git lfs install --local
git lfs pull
cmake -S . -B build/clean -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/clean --parallel 2
ctest --test-dir build/clean --output-on-failure
```

`--local` confines filter settings to this repository. If a clone was made without LFS, run the local install and pull from its root after authorization. Avoid treating a source ZIP containing pointers as a complete build input; hydrate the payload or obtain an owner-authorized complete source archive.

## Local repository preparation

The delivery folder is a fresh working-tree export without private Git history/index or a remote. When the owner chooses to initialize it, configure Git LFS with `git lfs install --local` before adding the tracked file. Use `git check-attr filter diff merge text -- RuntimeAssets/compiled-recipe-families-v1/manual-procedure-graph/definitions.jsonl` to inspect the rule. A proper staged pointer must report the SHA-256 and size above. Do not commit the 137 MB payload as an ordinary Git blob.

A disposable repository verified the actual clean/index pointer and local smudge behavior: canonical 134-byte pointer, complete local LFS object, reconstructed bytes matching the original hash/size, original working payload unchanged, no remotes or network operations, and no global/system Git configuration changes. No commit/push or hosting verification occurred.

## Hosting and publication remain separate

Before an authorized upload, the owner must check the chosen host's LFS availability, storage/bandwidth allocation and budget controls. Usage may be limited or charged depending on the host/account plan; [GitHub's LFS billing documentation](https://docs.github.com/articles/about-billing-for-git-large-file-storage) explains its model. No account settings, budget, storage subscription, purchase or upload was changed here. No quota or price is promised.

This local LFS preparation resolves the known oversized ordinary-Git file configuration issue. It does not establish remote pointer/object availability, hosting costs, distribution rights or license compliance. Confirm project/JUCE licensing and original/derived curriculum authority before publication.
