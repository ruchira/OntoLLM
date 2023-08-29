# Commits that OntoLLM has skipped

As explained in the [README](README.md), OntoLLM is a derivative of OntoGPT, but with different criteria as to which models to include.  Therefore OntoLLM is closely tracking OntoGPT, but with the use of "git cherry-pick" rather than "git merge", so as to be able to easily skip the occasional commit that is inapplicable in the case of OntoLLM.  We review each upstream commit before deciding to include it in OntoLLM.  Below is a record of the commits that are skipped.  Note that many of the commits that OntoLLM does cherry-pick from OntoGPT involve merge conflicts which are resolved manually. Since git cherry-pick comprises much of the same functionality as git merge, we also skip various upstream commits that are just merges.

## Number of commits checked

When comparing with upstream, the total number of commits we have checked and
decided to either cherry-pick or skip is:

92

Date of the last upstream commit checked:

Aug 25, 2023

## Individual commits

Skipping 018521e, it just adds another OpenAI model.

Skipping 90d3eaa, it is just a merge and we have both of its parents already.

Skipping 213f1cd, it is just a merge and we have both of its parents already.

Skipping 605d4e6, it is just a merge and we have both of its parents already.

Skipping 78aa4d0, it is a merge of 605d4e6 (above) and [fa068d3](https://github.com/monarch-initiative/ontogpt/commit/fa068d38e4de5c0eebfd0ed2a4b9161f64df0399), which we have.

Skipping 0e8aaea, it is a merge of 78aa4d0 (above) and [45ac219](https://github.com/monarch-initiative/ontogpt/commit/45ac219eaba367fe7ae2c5cd2d51248aff4fc775), which we have.

Skipping fcc882b, it is a merge of 78aa4d0 (above) and 0e8aaea (above).

Skipping ea2fa05, it is a merge of fcc882b (above) and [95fe932](https://github.com/monarch-initiative/ontogpt/commit/95fe9324f583fcac7afd7aa4fb648914c537f4d0), which we have.

Skipping c53ed42, it is a merge of fcc882b (above) and ea2fa05 (above).

Skipping e942aff, as our src/ontollm/models.yaml differs.

Skipping a71f15a, it is a merge of c53ed42 (above) and [41f7ec9](https://github.com/monarch-initiative/ontogpt/commit/41f7ec9961a60724353ab828cad020a03e83d9ed), which we have.

Skipping 2b4e3cd, as our src/ontollm/models.yaml differs.

Skipping 2e335a2, it is a merge of c53ed42 (above) and [0c6c739](https://github.com/monarch-initiative/ontogpt/commit/0c6c739d7a2165f7241ee7d99d21d55dac43b862), which we have.

Skipping ef28de1, it is a merge of 2e335a2 (above) and [afc6b03](https://github.com/monarch-initiative/ontogpt/commit/afc6b036b6e077e9735c4896d0973021301e00db), which we have.

Skipping b43762b, it is a merge of 93dcd31 (above) and [ef28de1](https://github.com/monarch-initiative/ontogpt/commit/ef28de170b44fcc42f3c87d00e788c1e126fd557), which we have.

Skipping 63ddc0c, it is a merge of b43762b (above) and [fc9b8f7](https://github.com/monarch-initiative/ontogpt/commit/fc9b8f70654e7e699d4726436e14bb840455caef), which we have.

Skipping ac4c060, it is just a merge and we have both of its parents already.

Skipping c9b8d34, it pertains only to the OpenAI client.

Skipping a859db7, it is just a merge and we have both of its parents already.

Skipping cb9d8ba, it pertains only to the OpenAI client.

Skipping 4849f4c, it is just a merge which pertains only to the OpenAI client.
