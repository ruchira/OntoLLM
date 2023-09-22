import yaml
import time
import pprint
from oaklib import get_adapter

NULL_VALS = ['', 'Not mentioned', 'none mentioned', 'Not mentioned in the text', 
             'Not mentioned in the provided text.', 'No exposures mentioned in the text.', 
             'None', 'N/A', 'No exposures mentioned in the text.', 'None mentioned in the text', 
             'Not mentioned in the text.', 'None relevant', 'None mentioned in the text.', 
             'No gene to molecular activity relationships mentioned in the text.',
             'No genes mentioned', 'No genes mentioned in the text.']
lines = []
adapter = get_adapter("sqlite:obo:MONDO")
# output_file = "output_2000_0719.yaml"
# output_file = "output_100_0817.yaml"
# output_file = "output_100_0818.yaml"
output_file = "output_100.0911.yaml"

def tripleprint(dict):
    key = next(iter(dict))
    for i in range(len(dict[key])):
        curr = []
        for value in dict.values():
            curr.append(value[i])
        print(curr)
def forprint(lst):
    for elem in lst:
        print(elem)
def forprint_newline(lst):
    for elem in lst:
        print(elem)
        print("\n")
def nprint(lst, n):
    for i in range(n):
        print(lst[i])
def sleepprint(lst):
    for elem in lst:
        print(elem)
        time.sleep(0.5)
def enumprint(lst):
    for index, elem in enumerate(lst):
        print(str(index + 1) + ":\t" + str(elem))

with open(output_file, "r") as file:
    to_print = False
    # perpetuators = tuple(["  subject:", "  predicate:", "  object:", "    "])
    perpetuators = tuple(["    - subject:", "      predicate:", "      object:"])
    perpetuators = tuple(["    - subject:", "      predicate:", "      object:", "      qualifier:", "      subject_qualifier:", "      object_qualifier:"])
    for line in file:
        line = line.strip("\n")
        # if line.startswith("extracted_object:"):
        if line.startswith("  disease_cellular_process_relationships:") and not line.startswith("  disease_cellular_process_relationships: "):
        # if line.startswith(perpetuators):
            to_print = True
        # elif not line.startswith(perpetuators):
        # if line.startswith("named_entities:"):
        elif not line.startswith(perpetuators):
            to_print = False
        if to_print:
            lines.append(line)

cleaned_lines = [x for x in list(filter(lambda elem: not(elem.isspace()), lines)) if x.strip()]
cleaned_lines = [x for x in cleaned_lines if not x.startswith(tuple(["      qualifier:", "      subject_qualifier:", "      object_qualifier:", "  disease_cellular_process_relationships:"]))]

header = "    - subject:"
i = 0
while i < len(cleaned_lines):
    if cleaned_lines[i].startswith(header):
        for index, elem in enumerate(cleaned_lines[i+1:i+3]):
            if elem.startswith(header):
                next_index = i + 1 + index
                del cleaned_lines[i:next_index]
                i -= 1
    i += 1

cleaned_lines = [x.strip() for x in cleaned_lines]
for i, line in enumerate(cleaned_lines.copy()):
# for line in cleaned_lines:
    if line.startswith("- "):
        cleaned_lines[i] = line[2:]

grouped_lines = [cleaned_lines[n:n+3] for n in range(0, len(cleaned_lines), 3)]
trimmed_dict = {"diseases": [], "relationships": [], "cellular processes": []}
for group in grouped_lines:
    subject = group[0].split(":", 1)[1].strip()
    relation = group[1].split(":", 1)[1].strip()
    object = group[2].split(":", 1)[1].strip()
    trimmed_dict["diseases"].append(subject)
    trimmed_dict["relationships"].append(relation)
    trimmed_dict["cellular processes"].append(object)

for key, value in trimmed_dict.copy().items():
    for i, elem in enumerate(value):
        if elem.lower() in (val.lower() for val in NULL_VALS):
            for key, value in trimmed_dict.items():
                del value[i]

# subjects_with_chebi = []
# objects_with_ecto = []
subjects_with_mondo = []
mondo_go = []
key = next(iter(trimmed_dict))
for i in range(len(trimmed_dict[key])):
    curr = []
    for value in trimmed_dict.values():
        curr.append(value[i])
    # subjects_with_chebi.append(curr)
    mondo_go.append(curr)
    # objects_with_ecto.append(curr)
# subjects_with_chebi = [x for x in subjects_with_chebi if x[0].startswith("CHEBI:")]
mondo_go = [x for x in mondo_go if x[0].startswith("MONDO:") and x[2].startswith("GO:")]
# objects_with_ecto = [x for x in objects_with_ecto if x[2].startswith("ECTO:")]

forprint(mondo_go)

# forprint(subjects_with_mondo)

subjects_with_names = []
# for elem in subjects_with_chebi:
for elem in subjects_with_mondo:
    curr = elem[:]
    curr[0] = adapter.label(curr[0])
    subjects_with_names.append(curr)

# forprint(subjects_with_names)