# Commits that OntoLLM has skipped

As explained in the [README](README.md), OntoLLM is a derivative of OntoGPT, but with different criteria as to which models to include.  Therefore OntoLLM is closely tracking OntoGPT, but with the use of "git cherry-pick" rather than "git merge", so as to be able to easily skip the occasional commit that is inapplicable in the case of OntoLLM.  We review each upstream commit before deciding to include it in OntoLLM.  Below is a record of the commits that are skipped.  Note that many of the commits that OntoLLM does cherry-pick from OntoGPT involve merge conflicts which are resolved manually. Since git cherry-pick comprises much of the same functionality as git merge, we also skip various upstream commits that are just merges.

## Commits checked

Date of the last upstream commit checked:

October 19, 2023, upstream commit 63ba04a (skipped).

## Individual commits

Skipping 018521e, it just adds another OpenAI model.

Skipping 90d3eaa, it is just a merge and we have both of its parents already.

Skipping 213f1cd, it is just a merge and we have both of its parents already.

Skipping 605d4e6, it is just a merge and we have both of its parents already.

Skipping 78aa4d0, it is a merge of 605d4e6 (above) and [fa068d3](https://github.com/monarch-initiative/ontogpt/commit/fa068d38e4de5c0eebfd0ed2a4b9161f64df0399), which we [have](https://github.com/monarch-initiative/ontogpt/commit/1bd84e953985be32e872320de131987c4cadffcd).

Skipping 0e8aaea, it is a merge of 78aa4d0 (above) and [45ac219](https://github.com/monarch-initiative/ontogpt/commit/45ac219eaba367fe7ae2c5cd2d51248aff4fc775), which we [have](https://github.com/monarch-initiative/ontogpt/commit/f60b75a00b8b0826ecd0c0b705ab48401c01cd42).

Skipping fcc882b, it is a merge of 78aa4d0 (above) and 0e8aaea (above).

Skipping ea2fa05, it is a merge of fcc882b (above) and [95fe932](https://github.com/monarch-initiative/ontogpt/commit/95fe9324f583fcac7afd7aa4fb648914c537f4d0), which we [have](https://github.com/monarch-initiative/ontogpt/commit/07a7eb1001acdc3e55869f7e95f6c09e8e7ab7dc).

Skipping c53ed42, it is a merge of fcc882b (above) and ea2fa05 (above).

Skipping e942aff, as our src/ontollm/models.yaml differs.

Skipping a71f15a, it is a merge of c53ed42 (above) and [41f7ec9](https://github.com/monarch-initiative/ontogpt/commit/41f7ec9961a60724353ab828cad020a03e83d9ed), which we [have](https://github.com/monarch-initiative/ontogpt/commit/df9d13f4ae51114f2c721878d5259834312be879).

Skipping 2b4e3cd, as our src/ontollm/models.yaml differs.

Skipping 2e335a2, it is a merge of c53ed42 (above) and [0c6c739](https://github.com/monarch-initiative/ontogpt/commit/0c6c739d7a2165f7241ee7d99d21d55dac43b862), which we [have](https://github.com/monarch-initiative/ontogpt/commit/7725f23ddc161304026c85b538423fee6de9cb30).

Skipping ef28de1, it is a merge of 2e335a2 (above) and [afc6b03](https://github.com/monarch-initiative/ontogpt/commit/afc6b036b6e077e9735c4896d0973021301e00db), which we [have](https://github.com/monarch-initiative/ontogpt/commit/679c51bf49ef594fad4160206d77a40cd221e5ec).

Skipping b43762b, it is a merge of 93dcd31 (above) and [ef28de1](https://github.com/monarch-initiative/ontogpt/commit/ef28de170b44fcc42f3c87d00e788c1e126fd557), which we [have](https://github.com/monarch-initiative/ontogpt/commit/c7a05fe211169e375735869c0cc7b1e8e75f5b04).

Skipping 63ddc0c, it is a merge of b43762b (above) and [fc9b8f7](https://github.com/monarch-initiative/ontogpt/commit/fc9b8f70654e7e699d4726436e14bb840455caef), which we [have](https://github.com/monarch-initiative/ontogpt/commit/81887a0c0b917a7dd6edb9a13eb5994d06714166).

Skipping ac4c060, it is just a merge and we have both of its parents already.

Skipping c9b8d34, it pertains only to the OpenAI client.

Skipping a859db7, it is just a merge and we have both of its parents already.

Skipping cb9d8ba, it pertains only to the OpenAI client.

Skipping 4849f4c, it is just a merge which pertains only to the OpenAI client.

Skipping 901b661, it is a merge of 4849f4c (above) and [3991a98](https://github.com/ruchira/OntoLLM/commit/3991a988a764c536b2464bf57c53cec65afbe711), which we [have](https://github.com/monarch-initiative/ontogpt/commit/519e557afc5a0def4f62cd1a653b3f4d9d2733fc).

Skipping e76e01f, it pertains only to an OpenAI model.

Skipping 24e4f8a, it is a merge of 901b661 (above) and e76e01f (above).

Skipping 01ea11c, it is just a merge and we have both of its parents already.

Skipping ce72628, it is just a merge and we have both of its parents already.

Skipping ca2dfd8, it is a merge of ce72628 (above) and
[cf1568e](https://github.com/monarch-initiative/ontogpt/commit/cf1568e76ca0ca803a18c57bd1abd420b92fcb57),
which we
[have](https://github.com/monarch-initiative/ontogpt/commit/88ed55b56424568992dabd7926f3f7f09aa75d7e).

Skipping 39c2b1e, it is just a merge and we have both of its parents already.

Skipping 24b52ce, it is a merge of 39c2b1e (above) and [1d17905](https://github.com/ruchira/OntoLLM/commit/1d179054aacf0e8bf032305041478a24cc541c88), which we [have](https://github.com/ruchira/OntoLLM/commit/a3dcd0a503d9314de1a479843d56aed396998b0c).

Skipping 3b3e146, it is a merge of 24b52ce (above) and [8298484](https://github.com/ruchira/OntoLLM/commit/82984842c96a652c25674b8197d82df7a0006236), which we [have](https://github.com/ruchira/OntoLLM/commit/4f603158ebbd6b077ed0f9e77418b61b8882f00e).

Skipping fa631c7, it is just a merge and we have both of its parents already.

Skipping 0c4e81b, it pertains to another branch make-kgx-tsv.

Skipping ba59fc2, it is just a merge and we have both of its parents already.

Skipping bb45238, it is a merge of ba59fc2 (above) and [e046924](https://github.com/ruchira/OntoLLM/commit/e046924a0133068d289af8eeba84ab4ccfb451ce), which we [have](https://github.com/ruchira/OntoLLM/commit/fd42c5dc572b9aaef431a873a13b000ee3e7847e).

Skipping a924756, it pertains to another branch 201-use-mypy-type-checking.

Skipping e9cb6ff, it is a merge of bb45238 (above) and [b6f6997](https://github.com/ruchira/OntoLLM/commit/b6f6997c35f2ae42594201faffe9d59cfba4c4a4), which we [have](https://github.com/ruchira/OntoLLM/commit/c6fab144856d6f4b4dd7b7792b9e213e77418aca).

Skipping ba40fee, it is just a merge and we have both of its parents already.

Skipping 9ff40c3, it only pertains to OpenAI models.

Skipping 4487b91, it only pertains to OpenAI models.

Skipping 8163bb4, it only pertains to OpenAI models.

Skipping 28d35fe, it only pertains to OpenAI models.

Skipping c620966, it only pertains to OpenAI models.

Skipping f11f551, it only pertains to OpenAI models.

Skipping ae04909, it only pertains to OpenAI models.

Skipping 586c851, it only pertains to OpenAI models.

Skipping 436247c, it is just a merge and we have both of its parents already.

Skipping 4ac7322, it is a merge of 436247c (above) and [3675ad7](https://github.com/ruchira/OntoLLM/commit/3675ad7ec7157a3874c865390f0bddc1d71bb784), which we [have](https://github.com/ruchira/OntoLLM/commit/72eb2b1f5b153ed25f6bffaa4afab5d80c781f8c).

Skipping 1125d83, it is a merge of 4ac7322 (above) and [941d250](https://github.com/ruchira/OntoLLM/commit/941d2503a63bcd02fec514a1671a163faf7ca296), which we [have](https://github.com/ruchira/OntoLLM/commit/c4df46390ab17118ef59e46a4a5a1a3a8151dbb0).

Skipping 8592321, it is a merge of 1125d83 (above) and [9e76716](https://github.com/ruchira/OntoLLM/commit/9e767167419a66c4f4ca8ca9fa650aabb3382af0), which we [have](https://github.com/ruchira/OntoLLM/commit/423be972aa09771ef8b689fcc659265b1479d07a0).

Skipping 7ed1310, it is a merge of 85292321 (above) and [73f910f](https://github.com/ruchira/OntoLLM/commit/73f910fb508bac0f9fe77497390401769cfa3db6), which we [have](https://github.com/ruchira/OntoLLM/commit/0a6065f210361157dcfcdd533f45cc03c4b9884b).

Skipping 7838cce, it is a merge of 7ed1310 (above) and [96aa7e5](https://github.com/ruchira/OntoLLM/commit/96aa7e5575f887dad043db17dd73cff11dba827d), which we [have](https://github.com/ruchira/OntoLLM/commit/ecb8d82cf15f366fd97b60c5a4674aaa4c301fb7).

Skipping 4004f23, it is a merge of 7838cce (above) and [2894883](https://github.com/ruchira/OntoLLM/commit/2894883a58bfb07b64efcf1c9a3e39473cc24bd1), which we [have](https://github.com/ruchira/OntoLLM/commit/a2f03a8e0408fe3d1d470e5662a08550f447f803).

Skipping bf0fb5e, it is a merge of 4004f23 (above) and [c950c2f](https://github.com/ruchira/OntoLLM/commit/c950c2f205b580157ac1e04f01e17eb8eaec5257), which we [have](https://github.com/ruchira/OntoLLM/commit/15ff0332e5af2e218094dba930cba3a4eacd6a9a).

Skipping 779a8b5, it is a merge of bf0fb5e (above) and [7958b3c](https://github.com/ruchira/OntoLLM/commit/7958b3ce1fc060a6ad8eaeb62587ccb09945419a), which we [have](https://github.com/ruchira/OntoLLM/commit/6db09cfefd19d7f2039c50bf9b50a3238353d564).

Skipping caf21e8, it is a merge of 779a8b5 (above) and [c4933ee](https://github.com/ruchira/OntoLLM/commit/c4933ee12f0f1bfec5929354733c9b2e616ee718), which we [have](https://github.com/ruchira/OntoLLM/commit/684a4eac1dc0fa5ae323edc412da5f9f5a45eafa).

Skipping bbf9873, it is a merge of 779a8b5 (above) and caf21e8 (above).

Skipping bc90974, it only pertains to OpenAI models.

Skipping c35f3ef, it is a merge of bbf9873 (above) and [f121b33](https://github.com/ruchira/OntoLLM/commit/f121b33caf6f3b640c57571a816abfb790e5afbf), which we [have](https://github.com/ruchira/OntoLLM/commit/8c4bd1cf59417a33036dc9aadf9da48e04503d72).

Skipping 40f2182, it is a merge of c35f3ef (above) and [b33e201](https://github.com/ruchira/OntoLLM/commit/b33e201ebf30a8b6e71aec4c373b62043bd6f8ee), which we [have](https://github.com/ruchira/OntoLLM/commit/8a3ca8e5439974dfdd6f3151435cc7f274aac59e).

Skipping 3f1202a, it is a merge of 40f2182 (above) and [7c4d424](https://github.com/ruchira/OntoLLM/commit/7c4d42498f87b8d755382bd76e4e6ab9466bf08d), which we [have](https://github.com/ruchira/OntoLLM/commit/e3b4173374ae9ff0735c5c8f201372c837d16d12).

Skipping 63ba04a, it is a merge of 3f1202a (above) and [c8d04cf](https://github.com/ruchira/OntoLLM/commit/c8d04cf71ed57e1ce8d6a766bd681cdff6db2d35), which we [have](https://github.com/ruchira/OntoLLM/commit/2c41e8cbed9408586ea6a1e692df84cb1fd358cc).
