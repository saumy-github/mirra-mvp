from exp_lib import *

MIA = ASSETS / "Female" / "FV2.1_Mia.avt"
base_ref = feats_avt(MIA)
print("fresh:", fresh(MIA))
f = readout("e0_mia_baseline")
d = diff(base_ref, f)
print("baseline readout vs Mia.avt file: %d slots differ" % len(d), d[:10])
print("slot0..2,5,6,8:", [round(f[i], 2) for i in (0, 1, 2, 5, 6, 8)])
