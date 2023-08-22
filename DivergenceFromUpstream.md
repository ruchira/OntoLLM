# Commits that OntoLLM has skipped

As explained in README.md, OntoLLM is a derivative of OntoGPT, but with different criteria as to which models to include.  Therefore OntoLLM is closely tracking OntoGPT, but with the use of "git cherry-pick" rather than "git merge", so as to be able to easily skip the occasional commit that is inapplicable in the case of OntoLLM.  We review each upstream commit before deciding to include it in OntoLLM.  Below is a record of the commits that are skipped.  Note that many of the commits that OntoLLM does cherry-pick from OntoGPT involve merge conflicts which are resolved manually. Since git cherry-pick comprises much of the same functionality as git merge, we also skip various upstream commits that are just merges.

## Number of commits checked

When comparing with upstream, the total number of commits we have checked and
decided to either cherry-pick or skip is:

77

Date of the last upstream commit checked:

Aug 15, 2023

## Individual commits

Skipping 018521e, it just adds another OpenAI model.

Skipping 90d3eaa, it is just a merge and we have both of its parents already.

Skipping 213f1cd, it is just a merge and we have both of its parents already.

Skipping 605d4e6, it is just a merge and we have both of its parents already.

Skipping 78aa4d0, it is a merge of 605d4e6 (above) and fa068d3, which we have.

Skipping 0e8aaea, it is a merge of 78aa4d0 (above) and 45ac219, which we have.

Skipping fcc882b, it is a merge of 78aa4d0 (above) and 0e8aaea (above).

Skipping ea2fa05, it is a merge of fcc882b (above) and 95fe932, which we have.

Skipping c53ed42, it is a merge of fcc882b (above) and ea2fa05 (above).

Skipping e942aff, as our src/ontollm/models.yaml differs.

Skipping a71f15a, it is a merge of c53ed42 (above) and 41f7ec9, which we have.

Skipping 2b4e3cd, as our src/ontollm/models.yaml differs.

Skipping 2e335a2, it is a merge of c53ed42 (above) and 0c6c739, which we have.

Skipping ef28de1, it is a merge of 2e335a2 (above) and afc6b03, which we have.

Skipping b43762b, it is a merge of 93dcd31 (above) and ef28de1, which we have.

Skipping 63ddc0c, it is a merge of b43762b (above) and fc9b8f7, which we have.
