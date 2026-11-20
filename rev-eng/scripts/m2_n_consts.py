import sys; sys.path.insert(0,r"C:\D-drive-data\mirra-mvp\rev-eng\scripts")
import disasm_fn4 as d
for a in (0x14897EDF0,0x14897EE00,0x14897ED70):
    print(hex(a), d.read_va(a,16))
