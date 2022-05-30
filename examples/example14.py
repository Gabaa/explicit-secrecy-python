import expsec

# Unsafe: assigning secret value into public list turns list secret
lst = [0]
expsec.declassify(lst)
lst[expsec.Public(0)] = 10  # Assign secret into public
print(lst)                  # ERROR
