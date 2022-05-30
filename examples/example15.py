import expsec

a = expsec.Public(10)
lst = [0]
expsec.declassify(lst)
lst[0] = a
print(lst)
