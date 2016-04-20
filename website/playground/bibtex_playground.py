import bibtexparser

with open('froehlich_citations.bib') as bibtex_file:
    bibtex_str = bibtex_file.read()

bib_database = bibtexparser.loads(bibtex_str)

# print(bib_database.entries)

for entry in bib_database.entries:
    print(entry['title'])