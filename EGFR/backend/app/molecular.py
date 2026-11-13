import base64
import math
from io import BytesIO

from rdkit import Chem
from rdkit.Chem import AllChem, Crippen, Descriptors, Draw, Lipinski, rdMolDescriptors


MAX_3D_HEAVY_ATOMS = 100
MAX_3D_TOTAL_ATOMS = 300


def parse_molecule(smiles: str) -> Chem.Mol:
    normalized_smiles = smiles.strip()
    if not normalized_smiles:
        raise ValueError("SMILES string must not be empty.")

    molecule = Chem.MolFromSmiles(normalized_smiles)
    if molecule is None:
        raise ValueError("The supplied string is not a valid SMILES structure.")
    return molecule


def canonicalize_smiles(molecule: Chem.Mol) -> str:
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def calculate_descriptors(molecule: Chem.Mol) -> dict[str, float | int]:
    return {
        "molecular_weight_da": round(Descriptors.MolWt(molecule), 3),
        "crippen_logp": round(Crippen.MolLogP(molecule), 3),
        "tpsa_a2": round(rdMolDescriptors.CalcTPSA(molecule), 3),
        "h_bond_donors": int(Lipinski.NumHDonors(molecule)),
        "h_bond_acceptors": int(Lipinski.NumHAcceptors(molecule)),
    }


def depict_molecule_png(molecule: Chem.Mol) -> str:
    image = Draw.MolToImage(molecule, size=(640, 420), kekulize=True)
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def generate_3d_coordinates(smiles: str) -> dict[str, object]:
    molecule = parse_molecule(smiles)
    heavy_atom_count = molecule.GetNumHeavyAtoms()
    if heavy_atom_count > MAX_3D_HEAVY_ATOMS:
        raise ValueError(
            f"3D generation is limited to {MAX_3D_HEAVY_ATOMS} heavy atoms per structure."
        )

    molecule = Chem.AddHs(molecule)
    if molecule.GetNumAtoms() > MAX_3D_TOTAL_ATOMS:
        raise ValueError(
            f"3D generation is limited to {MAX_3D_TOTAL_ATOMS} atoms including hydrogens."
        )

    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = 2026
    parameters.numThreads = 1
    parameters.maxIterations = 500
    try:
        embed_status = AllChem.EmbedMolecule(molecule, parameters)
    except (RuntimeError, ValueError) as error:
        raise ValueError("RDKit could not generate a 3D conformer for this structure.") from error
    if embed_status != 0:
        raise ValueError("RDKit could not generate a 3D conformer for this structure.")

    force_field_name = "none"
    optimization_converged: bool | None = None
    try:
        mmff_properties = AllChem.MMFFGetMoleculeProperties(molecule)
        if mmff_properties is not None:
            force_field = AllChem.MMFFGetMoleculeForceField(molecule, mmff_properties)
            force_field_name = "MMFF94"
        else:
            force_field = None
    except (RuntimeError, ValueError):
        force_field = None

    if force_field is None:
        try:
            force_field = AllChem.UFFGetMoleculeForceField(molecule)
            if force_field is not None:
                force_field_name = "UFF"
        except (RuntimeError, ValueError):
            force_field = None

    if force_field is not None:
        try:
            optimization_converged = force_field.Minimize(maxIts=300) == 0
        except (RuntimeError, ValueError) as error:
            raise ValueError("RDKit could not optimize the generated 3D conformer.") from error

    conformer = molecule.GetConformer()
    atoms = []
    for atom in molecule.GetAtoms():
        position = conformer.GetAtomPosition(atom.GetIdx())
        coordinates = {"x": float(position.x), "y": float(position.y), "z": float(position.z)}
        if not all(math.isfinite(value) for value in coordinates.values()):
            raise ValueError("RDKit generated invalid coordinates for this structure.")
        atoms.append(
            {
                "index": atom.GetIdx(),
                "element": atom.GetSymbol(),
                "formal_charge": atom.GetFormalCharge(),
                "aromatic": atom.GetIsAromatic(),
                "coordinates": coordinates,
            }
        )

    bonds = [
        {
            "begin": bond.GetBeginAtomIdx(),
            "end": bond.GetEndAtomIdx(),
            "order": bond.GetBondTypeAsDouble(),
            "aromatic": bond.GetIsAromatic(),
        }
        for bond in molecule.GetBonds()
    ]

    return {
        "smiles": canonicalize_smiles(Chem.RemoveHs(molecule)),
        "atoms": atoms,
        "bonds": bonds,
        "optimization": {
            "force_field": force_field_name,
            "converged": optimization_converged,
        },
    }


def fingerprint_array(molecule: Chem.Mol):
    import numpy as np
    from rdkit import DataStructs
    from rdkit.Chem import rdFingerprintGenerator

    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    fingerprint = generator.GetFingerprint(molecule)
    array = np.zeros((2048,), dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fingerprint, array)
    return array
