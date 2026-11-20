from exp_lib import *
MIA = ASSETS / "Female" / "FV2.1_Mia.avt"
REF = FEM_RES / "random-weight-female.avt"
fresh(MIA); V0 = mesh_vertices("m_mia"); print("Mia mesh", V0.shape, "y range", V0[:,1].min(), V0[:,1].max())
np.save(WORK / "V_mia.npy", V0)
fresh(REF); V1 = mesh_vertices("m_ref70"); print("ref70 mesh", V1.shape, "y range", V1[:,1].min(), V1[:,1].max())
np.save(WORK / "V_ref70.npy", V1)
print("default vs ref70 vertex distance:", vdist(V0, V1))
