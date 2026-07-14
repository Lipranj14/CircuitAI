"""Quick test of the SVG renderer."""
from schemas.domain import (
    CircuitGraph, DetectedComponent, BoundingBox, Pin,
    WireSegment, Junction, Point
)
from circuit_vision.svg_renderer import SVGRenderer

# Create a test circuit
circuit = CircuitGraph(
    components=[
        DetectedComponent(
            id='c1', type='resistor', label='R1', value='1k',
            bbox=BoundingBox(x=100, y=200, w=80, h=40),
            pins=[Pin(name='pin1', x=100, y=220), Pin(name='pin2', x=180, y=220)]
        ),
        DetectedComponent(
            id='c2', type='battery', label='V1', value='9V',
            bbox=BoundingBox(x=300, y=200, w=60, h=40),
            pins=[Pin(name='pin1', x=300, y=220), Pin(name='pin2', x=360, y=220)]
        ),
        DetectedComponent(
            id='c3', type='ground', label='GND',
            bbox=BoundingBox(x=200, y=350, w=40, h=40),
            pins=[Pin(name='pin1', x=220, y=350)]
        ),
        DetectedComponent(
            id='c4', type='opamp', label='OP1',
            bbox=BoundingBox(x=500, y=180, w=80, h=60),
            pins=[
                Pin(name='inv', x=500, y=198),
                Pin(name='noninv', x=500, y=222),
                Pin(name='out', x=580, y=210)
            ]
        ),
        DetectedComponent(
            id='c5', type='transistor_npn', label='Q1',
            bbox=BoundingBox(x=700, y=180, w=60, h=60),
            pins=[
                Pin(name='base', x=700, y=210),
                Pin(name='collector', x=760, y=195),
                Pin(name='emitter', x=760, y=225)
            ]
        ),
    ],
    wires=[
        WireSegment(id='w1', start=Point(x=180, y=220), end=Point(x=300, y=220)),
        WireSegment(id='w2', start=Point(x=360, y=220), end=Point(x=500, y=220)),
        WireSegment(id='w3', start=Point(x=580, y=210), end=Point(x=700, y=210)),
    ],
    junctions=[
        Junction(id='j1', position=Point(x=300, y=220)),
    ],
    nodes=[],
    labels=[],
    image_width=900,
    image_height=500,
)

renderer = SVGRenderer(dark_mode=True)
svg = renderer.render(circuit)

print(f"SVG generated: {len(svg)} characters")
print(f"Contains svg tag: {'svg' in svg}")
print(f"Contains resistor: {'resistor' in svg}")
print(f"Contains R1 label: {'R1' in svg}")
print(f"Contains opamp: {'opamp' in svg}")
print(f"Contains transistor: {'transistor' in svg}")

# Save to file for inspection
with open("test_output.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("Saved to test_output.svg")
print("SVG rendering: OK")
