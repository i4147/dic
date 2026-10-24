c = 0
nl = []
data = ""
xtr = []
with open("en.txt") as f:
    data = f.read()
lines = data.splitlines(keepends=True)
for line in lines:
    word = line.strip()
    if word.endswith(("aceae", "idae", "ales", "inae", "oidae", "iformes")):
        xtr.append(line)
    else:
        nl.append(line)
        c += 1
print(c)
with open("non", "w") as f:
    for k in xtr:
        f.write(k)
with open("cleaned", "w") as f:
    for k in nl:
        f.write(k)
