"""
Unsafe: assigning secret value into public list turns list secret

expsec_public: lst
"""

a = 10
lst = [0]
lst[0] = a  # Assign secret into public
print(lst)  # ERROR
