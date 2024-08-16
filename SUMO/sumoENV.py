import copy
from dataclasses import dataclass, field
import libsumo as traci
from sumolib import checkBinary
from .sumoTrafficLightStatus import trafficLightStatus as tls


def getDirection(local_x, local_y, x, y) -> str:
    """get direction from local junction to target junction"""
    if x <= local_x and y < local_y:
        return "n"
    if x < local_x and y >= local_y:
        return "w"
    if x >= local_x and y > local_y:
        return "s"
    if x > local_x and y <= local_y:
        return "e"

    raise ValueError(
        f"direction error x:{x}, y:{y} are some as local_x:{local_x}, local_y:{local_y}"
    )


@dataclass
class junctionTrafficInfo:
    """record junction traffic info"""

    env_step: int = 0
    junction_id: str = ""

    w_i_mean_speed: float = 0
    s_i_mean_speed: float = 0
    e_i_mean_speed: float = 0
    n_i_mean_speed: float = 0

    w_o_mean_speed: float = 0
    s_o_mean_speed: float = 0
    e_o_mean_speed: float = 0
    n_o_mean_speed: float = 0

    w_i_vehicles: set = field(default_factory=set)
    s_i_vehicles: set = field(default_factory=set)
    e_i_vehicles: set = field(default_factory=set)
    n_i_vehicles: set = field(default_factory=set)

    w_o_vehicles: set = field(default_factory=set)
    s_o_vehicles: set = field(default_factory=set)
    e_o_vehicles: set = field(default_factory=set)
    n_o_vehicles: set = field(default_factory=set)

    w_transfer_rate: float = 0
    s_transfer_rate: float = 0
    e_transfer_rate: float = 0
    n_transfer_rate: float = 0

    def __iadd__(self, other: "junctionTrafficInfo"):
        """Add previous step info to current step info"""
        new_step = getattr(self, "env_step") + 1
        mean_speeds = [
            "w_i_mean_speed",
            "s_i_mean_speed",
            "e_i_mean_speed",
            "n_i_mean_speed",
            "w_o_mean_speed",
            "s_o_mean_speed",
            "e_o_mean_speed",
            "n_o_mean_speed",
        ]
        vehicles = [
            "w_i_vehicles",
            "s_i_vehicles",
            "e_i_vehicles",
            "n_i_vehicles",
            "w_o_vehicles",
            "s_o_vehicles",
            "e_o_vehicles",
            "n_o_vehicles",
        ]

        for attr in mean_speeds:
            total_speed = getattr(self, attr) * self.env_step + getattr(other, attr)
            setattr(self, attr, total_speed / new_step)

        for vehicle in vehicles:
            new_set = getattr(self, vehicle).union(getattr(other, vehicle))
            setattr(self, vehicle, new_set)

        self.env_step = new_step

        return self

    def __itruediv__(self, other: "junctionTrafficInfo"):
        """Calculate transfer rate form other junction to self junction"""
        local_x, local_y = [int(i) for i in self.junction_id.split("-")[:2]]
        x, y = [int(i) for i in other.junction_id.split("-")[:2]]
        direction = getDirection(local_x, local_y, x, y)
        other_vehicles_num = other.getTaTolVehiclesNum()

        transfer_rate = (
            0
            if other_vehicles_num == 0
            else len(getattr(other, f"{direction}_i_vehicles")) / other_vehicles_num
        )

        setattr(self, f"{direction}_transfer_rate", transfer_rate)

        return self

    def getTaTolVehiclesNum(self):
        """ "get total vehicles number in this junction"""
        return (
            len(self.w_i_vehicles)
            + len(self.s_i_vehicles)
            + len(self.e_i_vehicles)
            + len(self.n_i_vehicles)
        )


class sumoENV:
    """Abstracted and encapsulated simulation environment"""

    def __init__(
        self,
        path: str,
        GUI: bool = False,
        yellow_status_time: int = 5,
        cycle_time: int = 10,
    ):
        sumoMode = "sumo-gui" if GUI else "sumo"
        sumoBinary = checkBinary(sumoMode)
        sumoCmd = [sumoBinary, "-c", path]

        traci.start(sumoCmd)
        print("sumo started!")

        self.yellow_status_time = yellow_status_time
        self.cycle_time = cycle_time

        self.resetEnvRecord()
        self.resetTrafficLights()

    def __del__(self) -> None:
        traci.close()
        print("sumo closed!")

    def nextStep(self):
        return self.nextSimulationStep(self.cycle_time - self.yellow_status_time, True)

    def nextSimulationStep(self, num, return_record=False):
        for _ in range(num):
            traci.simulationStep()
            self.addEnvRecord()

        if return_record:
            self.calculateTransferRate()
            result = copy.deepcopy(self.env_record)
            self.resetEnvRecord()

            return result
        else:
            return None

    def resetEnvRecord(self):
        self.env_record = {
            i: junctionTrafficInfo(junction_id=i) for i in self.getJunctionList()
        }

    def addEnvRecord(self):
        for junction_id in self.getJunctionList():
            self.env_record[junction_id] += self.getJunctionTrafficInfo(junction_id)

    def getJunctionTrafficInfo(self, junction_id) -> junctionTrafficInfo:
        result = {}
        edges = self.getJunctionEdgesInfo(junction_id)

        for k, v in edges.items():
            result[k + "_mean_speed"] = traci.edge.getLastStepMeanSpeed(v)
            result[k + "_vehicles"] = set(traci.edge.getLastStepVehicleIDs(v))

        return junctionTrafficInfo(**result)

    def getJunctionEdgesInfo(self, junction_id) -> dict:
        result = {}
        local_x, local_y, _ = self.getJunctionInfo(junction_id)
        out_edges = [
            i
            for i in traci.junction.getOutgoingEdges(junction_id)
            if self.isEdgeLegal(i)
        ]
        in_edges = [
            i
            for i in traci.junction.getIncomingEdges(junction_id)
            if self.isEdgeLegal(i)
        ]

        for edge in out_edges:
            to_junction = traci.edge.getToJunction(edge)
            x, y, _ = self.getJunctionInfo(to_junction)
            direction = getDirection(local_x, local_y, x, y)

            result[f"{direction}_o"] = edge

        for edge in in_edges:
            from_junction = traci.edge.getFromJunction(edge)
            x, y, _ = self.getJunctionInfo(from_junction)
            direction = getDirection(local_x, local_y, x, y)

            result[f"{direction}_i"] = edge

        return result

    def getJunctionInfo(self, junction_id):
        x, y, junction_type = junction_id.split("-")

        return int(x), int(y), junction_type

    def isEdgeLegal(self, edge_id):
        return edge_id[0] != ":"

    def getJunctionList(self):
        junctions = traci.junction.getIDList()
        return [i for i in junctions if self.isJunctionLegal(i)]

    def isJunctionLegal(self, junction_id):
        if junction_id[0] == ":":
            return False
        _, _, junction_type = self.getJunctionInfo(junction_id)

        if junction_type == "end":
            return False

        return True

    def calculateTransferRate(self):
        for i in self.getJunctionList():
            self.calculateJunctionTransferRate(i)

    def calculateJunctionTransferRate(self, junction_id):
        in_edges = traci.junction.getIncomingEdges(junction_id)

        for edge in in_edges:
            from_junction = traci.edge.getFromJunction(edge)
            _, _, junction_type = self.getJunctionInfo(from_junction)

            if junction_id == from_junction:
                continue

            if junction_type == "end":
                continue

            self.env_record[junction_id] /= self.env_record[from_junction]

    def getJunctionVehiclesNum(self, junction_id):
        vehicles = set(
            self.env_record[junction_id].w_i_vehicles
            + self.env_record[junction_id].s_i_vehicles
            + self.env_record[junction_id].e_i_vehicles
            + self.env_record[junction_id].n_i_vehicles
        )

        return len(list(vehicles))

    def changeTrafficLights(self, states: dict[str, str]):
        next_states = {
            junction: self.getJunctionTrafficLightStateDefine(junction, state)
            for junction, state in states.items()
        }

        for junction, next_state in next_states.items():
            if next_state != self.getJunctionTrafficLightState(junction):
                self.setYellowState(junction, states[junction])

        self.nextSimulationStep(self.yellow_status_time)

        for junction, next_state in next_states.items():
            traffic_light_id = self.getJunctionTrafficLightId(junction)
            traci.trafficlight.setRedYellowGreenState(traffic_light_id, next_state)

    def getJunctionTrafficLightState(self, junction_id):
        traffic_light_id = self.getJunctionTrafficLightId(junction_id)
        return traci.trafficlight.getRedYellowGreenState(traffic_light_id)

    def getJunctionType(self, junction_id):
        _, _, junction_info = junction_id.split("-")
        junction_type, *arr = junction_info.split("_")

        if junction_type == "TJunction":
            return junction_type, junction_info[12:], arr[0]
        elif junction_type == "Junction":
            return junction_type, junction_info[9:], "x"

    def getJunctionTrafficLightStateDefine(self, junction_id, state):
        junction_type, junction_info, direction = self.getJunctionType(junction_id)
        if junction_type == "TJunction":
            return tls[junction_type][junction_info][direction][state]
        elif junction_type == "Junction":
            return tls[junction_type][junction_info][state]

    def getJunctionTrafficLightId(self, junction_id):
        x, y, _ = self.getJunctionInfo(junction_id)
        return f"{x}-{y}"

    def getConnectedJunctions(self, junction_id):
        out_edges = traci.junction.getOutgoingEdges(junction_id)
        out_edges = [i for i in out_edges if self.isEdgeLegal(i)]
        out_junctions = [traci.edge.getToJunction(i) for i in out_edges]
        junctions = [
            i for i in out_junctions if self.isConnectedJunctionLegal(junction_id, i)
        ]
        result = {}

        for junction in junctions:
            x, y, _ = self.getJunctionInfo(junction)
            local_x, local_y, _ = self.getJunctionInfo(junction_id)
            direction = getDirection(local_x, local_y, x, y)
            result[direction] = junction

        return result

    def isConnectedJunctionLegal(self, local_junction_id, target_junction_id):
        return (
            local_junction_id != target_junction_id and target_junction_id[:3] != "end"
        )

    def setYellowState(self, junction_id, state):
        traffic_light_id = self.getJunctionTrafficLightId(junction_id)
        yellow_state = self.getJunctionYellowStateDefine(junction_id, state)
        traci.trafficlight.setRedYellowGreenState(traffic_light_id, yellow_state)

    def getJunctionYellowStateDefine(self, junction_id, state):
        junction_type, junction_info, direction = self.getJunctionType(junction_id)
        if junction_type == "TJunction":
            return tls[junction_type][junction_info][direction][f"{state}_yellow"]
        elif junction_type == "Junction":
            return tls[junction_type][junction_info][f"{state}_yellow"]

    def resetTrafficLights(self):
        for junction in self.getJunctionList():
            traffic_light_id = self.getJunctionTrafficLightId(junction)
            state = self.getJunctionTrafficLightStateDefine(junction, "0")
            traci.trafficlight.setRedYellowGreenState(traffic_light_id, state)


if __name__ == "__main__":
    # env = sumoENV(path="./sumo/net/net.sumocfg", GUI=True)
    env = sumoENV(path="./sumo/QT/QT.sumocfg", GUI=True)
    while True:
        pass
