# Standard Protocols

ecproc ships with built-in protocol templates following established electrochemical testing standards.

## DOE Protocols

### ORR Catalyst Durability

Based on the U.S. Department of Energy accelerated stress test protocols for ORR catalysts.

```python
from ecproc.protocols.doe import ORRProtocol

protocol = ORRProtocol()
procedure = protocol.build()
```

### Catalyst Support Durability

DOE protocol for carbon support corrosion testing.

```python
from ecproc.protocols.doe import CatalystSupportProtocol

protocol = CatalystSupportProtocol()
procedure = protocol.build()
```

### OER Catalyst Durability

DOE-style protocol for oxygen evolution reaction catalyst testing.

```python
from ecproc.protocols.doe import OERProtocol

protocol = OERProtocol()
procedure = protocol.build()
```

## JRC Protocols

### PEM Fuel Cell

Joint Research Centre harmonized testing protocol for PEM fuel cells.

```python
from ecproc.protocols.jrc import PEMProtocol

protocol = PEMProtocol()
procedure = protocol.build()
```

### Alkaline Electrolysis

JRC protocol for alkaline water electrolysis durability.

```python
from ecproc.protocols.jrc import AlkalineProtocol

protocol = AlkalineProtocol()
procedure = protocol.build()
```

## Custom Protocols

All standard protocols extend `StandardProtocol`. Create your own:

```python
from ecproc.protocols.base import StandardProtocol
from ecproc.sdk.procedure import Procedure


class MyProtocol(StandardProtocol):
    name = "My Custom Protocol"
    version = "1.0"

    def build(self) -> Procedure:
        p = Procedure()
        p.system(electrodes=3, reference="RHE")

        with p.phase("Conditioning") as phase:
            phase.cv(between=(0.05, 1.2), rate=0.05, cycles=50)

        with p.phase("Measurement") as phase:
            phase.lsv(start=1.0, stop=0.2, rate=0.005)

        return p
```
