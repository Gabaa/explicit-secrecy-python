import expsec

# Should be safe (implicit flow)
h = 5
i = expsec.Public(0)
while i < h:
    i = i + expsec.Public(1)

print(i)
