"""Electrochemical technique definitions."""

from ecproc.sdk.techniques.ca import Hold, hold
from ecproc.sdk.techniques.cc import CC, cc
from ecproc.sdk.techniques.cp import Galvanostatic, galvanostatic
from ecproc.sdk.techniques.cv import CV, cv
from ecproc.sdk.techniques.dpv import DPV, dpv
from ecproc.sdk.techniques.eis import EIS, eis
from ecproc.sdk.techniques.gcd import GCD, gcd
from ecproc.sdk.techniques.lsv import LSV, lsv
from ecproc.sdk.techniques.ocp import OCP, ocp
from ecproc.sdk.techniques.stripping import Stripping, stripping
from ecproc.sdk.techniques.swv import SWV, swv

__all__ = [
    "ocp", "OCP",
    "cv", "CV",
    "lsv", "LSV",
    "eis", "EIS",
    "hold", "Hold",
    "galvanostatic", "Galvanostatic",
    "dpv", "DPV",
    "swv", "SWV",
    "gcd", "GCD",
    "cc", "CC",
    "stripping", "Stripping",
]
