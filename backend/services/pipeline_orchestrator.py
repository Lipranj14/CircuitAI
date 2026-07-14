import logging
from services.detector_service import DetectorService
from services.graph_service import GraphBuilderService
from services.knowledge_analysis_service import KnowledgeAnalysisService
from services.netlist_parser import NetlistParserService
from circuit_vision.repair_engine import AutoRepairEngine
from circuit_vision.svg_renderer import SVGRenderer
from schemas.domain import CircuitGraph

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.detector = DetectorService()
        self.graph_builder = GraphBuilderService()
        self.renderer = SVGRenderer(dark_mode=True)
        self.netlist_parser = NetlistParserService()

    async def run_pipeline(self, image_bytes: bytes, debug: bool = False) -> dict:
        # 1. Detect (Single-pass: components, netlist)
        logger.info("Pipeline: Running single-pass detection")
        result = await self.detector.detect_from_image(image_bytes)
        
        if not result.get("success"):
            raise ValueError(result.get("error", "Unknown detection error"))
            
        components = result["components"]
        netlist_nodes = result["nodes"]
        circuit = result["graph"]
        fallback = result.get("fallback", False)
        
        # 3. Enhance
        logger.info("Pipeline: Generating SVG and React Flow nodes")
        rf_nodes, rf_edges = self.graph_builder.to_react_flow(circuit)
        svg_string = self.renderer.render(circuit)
        
        logger.info("Pipeline: Running Auto-Repair Engine")
        repairs = AutoRepairEngine(circuit).analyze()
        
        logger.info("Pipeline: Running Knowledge Analysis")
        analysis = KnowledgeAnalysisService(circuit).run_analysis()
        
        payload = {
            "circuit": circuit.model_dump(),
            "svg": svg_string,
            "react_flow_nodes": rf_nodes,
            "react_flow_edges": rf_edges,
            "nodes": rf_nodes,
            "edges": rf_edges,
            "repairs": [r.model_dump() for r in repairs],
            "analysis": analysis.model_dump(),
            "overview": result.get("overview", ""),
            "fallback": fallback
        }
        
        if debug:
            payload["debug_outputs"] = {
                "components": [c.model_dump() for c in components],
                "netlist_nodes": netlist_nodes,
            }
            
        return payload

    async def run_pipeline_from_netlist(self, netlist_text: str, debug: bool = False) -> dict:
        logger.info("Pipeline: Running netlist parsing")
        result = await self.netlist_parser.parse_netlist(netlist_text)
        
        if not result.get("success"):
            raise ValueError(result.get("error", "Unknown netlist parsing error"))
            
        components = result["components"]
        netlist_nodes = result["nodes"]
        
        # Build Graph
        circuit = self.graph_builder.build_graph(
            components=components,
            netlist_nodes=netlist_nodes,
            labels=[],
            img_w=800,
            img_h=600
        )
        fallback = False
        
        logger.info("Pipeline: Generating SVG and React Flow nodes")
        rf_nodes, rf_edges = self.graph_builder.to_react_flow(circuit)
        svg_string = self.renderer.render(circuit)
        
        logger.info("Pipeline: Running Auto-Repair Engine")
        repairs = AutoRepairEngine(circuit).analyze()
        
        logger.info("Pipeline: Running Knowledge Analysis")
        analysis = KnowledgeAnalysisService(circuit).run_analysis()
        
        payload = {
            "circuit": circuit.model_dump(),
            "svg": svg_string,
            "react_flow_nodes": rf_nodes,
            "react_flow_edges": rf_edges,
            "nodes": rf_nodes,
            "edges": rf_edges,
            "repairs": [r.model_dump() for r in repairs],
            "analysis": analysis.model_dump(),
            "fallback": fallback
        }
        
        if debug:
            payload["debug_outputs"] = {
                "components": [c.model_dump() for c in components],
                "netlist_nodes": netlist_nodes,
            }
            
        return payload

