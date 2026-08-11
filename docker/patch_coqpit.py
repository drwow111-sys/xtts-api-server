"""
Patch applied at Docker build time to the installed `coqpit` package.

Known upstream bug (see daswer123/xtts-api-server#94): coqpit's Union/type
detection breaks on Python 3.10+'s `X | Y` union syntax (`types.UnionType`),
which then makes `issubclass(field_type, Serializable)` raise
`TypeError: issubclass() arg 1 must be a class` while loading the XTTS model
config - crashing the server on every boot. Community-verified fix (same
issue thread) patches two spots in coqpit/coqpit.py. No compatible upstream
release exists yet, so we patch the installed file directly at image build
time rather than forking coqpit itself.
"""
import coqpit
import pathlib

path = pathlib.Path(coqpit.__file__).parent / "coqpit.py"
src = path.read_text()

old_union_check = (
    "    try:\n"
    "        return safe_issubclass(arg_type.__origin__, Union)\n"
    "    except AttributeError:\n"
)
new_union_check = (
    "    if type(arg_type).__name__ == \"UnionType\":\n"
    "        return True\n"
    "    try:\n"
    "        return safe_issubclass(arg_type.__origin__, Union)\n"
    "    except AttributeError:\n"
)

old_deserialize = (
    "    if issubclass(field_type, Serializable):\n"
    "        return field_type.deserialize_immutable(x)\n"
    "    raise ValueError(f\" [!] '{type(x)}' value type of '{x}' does not match '{field_type}' field type.\")\n"
)
new_deserialize = (
    "    try:\n"
    "        if issubclass(field_type, Serializable):\n"
    "            return field_type.deserialize_immutable(x)\n"
    "    except TypeError:\n"
    "        pass\n"
    "    return x\n"
)

if old_union_check not in src:
    raise SystemExit("patch_coqpit: union-check anchor text not found, coqpit source has changed - update the patch")
if old_deserialize not in src:
    raise SystemExit("patch_coqpit: deserialize anchor text not found, coqpit source has changed - update the patch")

src = src.replace(old_union_check, new_union_check)
src = src.replace(old_deserialize, new_deserialize)
path.write_text(src)
print(f"patch_coqpit: patched {path}")
