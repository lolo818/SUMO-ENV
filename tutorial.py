import libsumo as traci

def main():
    sumoCmd = ["sumo-gui", "-c", "SUMO/QT/QT.sumocfg"]
    traci.start(sumoCmd)

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

    traci.close()


if __name__ == "__main__":
    main()