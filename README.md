# From SCOR Models to Decision Support: A Transferable and Composable Simulation Framework for Supply Chain Digital Twins

Open-source Python implementation of a transferable, reusable and configurable methodology for translating SCOR process representations into executable supply chain simulation models. The repository contains the implementation, configuration files, input data and results of the study presented in the accompanying manuscript:

> "From SCOR Models to Decision Support: A Transferable and Composable Simulation Framework for Supply Chain Digital Twins"

The methodology is applied to two structurally different manufacturing supply chains, which share the same modelling approach but differ in fulfilment logic, operational policies, system structure and execution mechanism:

| | MTS: plastic injection | MTO: apparel |
|---|---|---|
| Fulfilment logic | Inventory-driven: periodic raw-material replenishment, production to a safety-stock target, delivery from finished-goods stock | Order-driven: order approval, prototyping (physical or digital), then order fulfilment |
| Execution mechanism | Fixed-increment, time-stepped simulation (weekly periods) | Discrete-event simulation with next-event time advance ([SimPy](https://simpy.readthedocs.io/)) |
| Stress-testing scenarios | Demand variation, supply interruption, supplier lead-time increase | Demand variation, physical vs digital prototyping |

## Methodology

The framework follows the sequence described in the manuscript:

1. **SCOR process representation** of Source, Make and Deliver for each case.
2. **BPMN 2.0 formalisation** of each case (diagrams provided in the Supplementary Materials of the manuscript).
3. **Translation into generic modelling constructs**: entities, resources, inventories and policies.
4. **Model configuration**: selection of the simulation engine and case parameters, kept in JSON files separate from the model logic (with the exceptions listed in [Known limitations](#known-limitations-and-scope-of-this-version)).
5. **Scenario definition and simulation execution.**
6. **Performance assessment** across four dimensions: operational, service, economic and environmental.

Each engine mirrors the SCOR structure: `core/mts/processes` and `core/mto/processes` contain the Source, Make and Deliver logic, `core/mto/workflows` orchestrates order approval, prototyping and fulfilment, and the `analytics` modules compute KPIs, costs, profit and environmental impact.

## Repository structure

```
.
├── cases/
│   ├── mts_case/
│   │   ├── config.json              # Baseline configuration (policy, costs, inventory, outputs)
│   │   ├── data/                    # Demand, bill of materials and suppliers (JSON)
│   │   ├── run.py                   # Baseline simulation
│   │   └── scenarios/               # Stress-testing experiments and scenarios_config.json
│   └── mto_case/
│       ├── config.json              # Baseline configuration
│       ├── data/                    # Orders and process parameters (JSON)
│       ├── run.py                   # Baseline simulation
│       └── scenarios/               # Stress-testing experiments and scenarios_config.json
├── core/
│   ├── mts/                         # Time-stepped engine: data, engine, entities, processes, simulation, analytics
│   └── mto/                         # SimPy engine: data, engine, entities, processes, resources, workflows, analytics
├── results/
│   ├── baseline/                    # Baseline outputs per case
│   └── experiments/                 # Scenario outputs and figures
├── requirements.txt
├── LICENSE
└── README.md
```

## Installation

Python 3.10 or higher is required (tested with Python 3.12). The only dependencies are `simpy`, `pandas`, `numpy` and `matplotlib`.

```bash
git clone https://github.com/beateruel/sc_sim_framework.git
cd sc_sim_framework
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the simulations

Run all commands from the repository root: configuration paths are relative to it and the code is imported as a package.

**Baseline simulations**

```bash
python -m cases.mts_case.run
python -m cases.mto_case.run
```

Outputs are written to `results/baseline/<case>/`.

**Stress-testing experiments**

```bash
# MTS
python -m cases.mts_case.scenarios.run_demand_variation
python -m cases.mts_case.scenarios.run_supply_interruption
python -m cases.mts_case.scenarios.run_lead_time_shock

# MTO
python -m cases.mto_case.scenarios.run_demand_variation
python -m cases.mto_case.scenarios.run_prototyping
```

Outputs are written to `results/experiments/<case>/`. Each run takes from a few seconds to about ten seconds on a standard laptop.

**Figures of the manuscript**

Once the experiments have been run, the summary figures (PDF and PNG) are generated from the experiment results with:

```bash
python -m core.mts.analytics.visualization.reporting_figures
python -m core.mto.analytics.visualization.reporting_figures
```

## Configuration

Each case is configured through JSON files. A small set of constants of the MTO engine is still defined in the code (see [Known limitations](#known-limitations-and-scope-of-this-version)).

**MTS (`cases/mts_case/config.json`)**

| Block | Content |
|---|---|
| `input_files` | Names of the demand, bill-of-materials and supplier files in `data/` |
| `simulation` | `demand_variation` (fractional change applied to demand) and `shortage_start_week` / `shortage_end_week` (supply interruption window; `-1` means no interruption) |
| `initial_inventory` | Initial raw-material and finished-goods inventory by item |
| `material_prices` | Raw-material price profile over time |
| `mts_policy` | `purchase_cycle_weeks`, `demand_coverage_weeks`, `distributor_release_cycle_weeks`, `weeks_per_month` |
| `costs`, `emissions`, `time` | Economic, environmental and transport/storage time parameters |
| `outputs`, `plots` | Output folder and plotting options |

**MTO (`cases/mto_case/config.json`)**

| Block | Content |
|---|---|
| `input_files` | Orders file and process-parameters file in `data/` |
| `simulation` | Simulation horizon in hours (`until`) and `prototyping_type` (`PHYSICAL` or `DIGITAL`) |
| `outputs` | Output folder and plotting options |

Process times, inventory policies, economic and environmental parameters of the MTO case are defined in `cases/mto_case/data/process_parameters.json`.

**Scenarios (`scenarios/scenarios_config.json`)**

| Case | Experiment | Values |
|---|---|---|
| MTS | Demand variation | -30% to +30% in steps of 10% |
| MTS | Supply interruption | 4, 8, 12 and 16 weeks, starting in week 9 |
| MTS | Supplier lead time | 12, 14, 16, 18 and 20 weeks |
| MTO | Demand variation | Demand multipliers from 0.7 to 1.3 in steps of 0.1 |
| MTO | Prototyping | `PHYSICAL` vs `DIGITAL` |

## Outputs

**MTS** (`results/baseline/mts_case/`)

- `operations/`: inventory, purchase orders, releases, production, distribution, weekly metrics and weekly demand.
- `kpis/`: OTIF, fill rate, stockouts, average inventory, inventory turnover, variability and peaks, throughput, production-plan fulfilment, production lead time and service level.
- `cost/`, `profit/`, `emissions/`: cost breakdown, profit and environmental impact.
- `visualization/`: inventory, finished-goods and demand plots.

**MTO** (`results/baseline/mto_case/`)

- `events/`: event log of the simulation.
- `kpis/`: lead time and OTIF per order.
- `cost/`, `profit/`, `emissions/`: cost, profit and environmental impact per order.
- `visualization/`: Gantt chart of the orders.

**Experiments** (`results/experiments/<case>/`)

- One summary CSV per experiment (`results_demand_variation.csv`, `results_shortage.csv`, `results_lead_time_shock.csv`, `results_prototyping.csv`).
- `visualization/`: per-scenario plots and the summary figures of the manuscript.

## Known limitations and scope of this version

This release is a first working implementation of the methodology (a minimum viable version) that reproduces the two cases of the manuscript.

**Parameters.** Some parameters in the JSON files are not used by the model, either because the value is defined in the code or because they are descriptive (for example, the maximum of a min/max range or the attributes of the bill of materials and suppliers). In addition, the following constants of the MTO engine are defined in the code and not in the JSON files:

- Duration factor of the digital design stage: 1.5 (`core/mto/workflows/prototype.py`). The digital design takes longer because it must be validated by the customer.
- Capacity of each resource (office, designer, operator, logistics): 6 (`core/mto/resources/resources.py`).
- Initial level and capacity of the sample-material, production-material and finished-goods inventories (`core/mto/resources/resources.py`).
- Working hours per day: 8 (`core/mto/utils/time_utils.py`). The `working_hours_per_day` value in `process_parameters.json` is not read.

**Scope of the models.**

- The models cover the Source, Make and Deliver processes. Plan and Return are not represented.
- The BPMN diagrams describe each process at the level of detail available for each case. The BPMN models are not executed: the simulation aggregates activities that share the same operational footprint (timing, resources and cost) into a smaller set of executable steps, as described in the manuscript.
- In the MTS case, the quality-rejection branch shown in the BPMN model is not implemented in the simulation.
- In the MTO case, order approval and the purchase order are represented in a simplified form.

## Reproducibility

- The simulations contain no random components: the same configuration and input files always produce the same results.
- Case data and parameters are separated from the model logic wherever possible, so most scenarios are defined by changing the JSON files without modifying the code. The exceptions are the constants listed in [Known limitations](#known-limitations-and-scope-of-this-version).
- The experiments reported in the manuscript are defined in the `scenarios_config.json` files and can be reproduced with the commands above.

## Citation

If you use this repository in academic work, please cite:

```bibtex
@article{royo2026_scor_executable,
  title={From SCOR Models to Decision Support: A Transferable and Composable Simulation Framework for Supply Chain Digital Twins},
  author={Royo, Beatriz and de la Cruz, Mar{\'\i}a Teresa},
  year={2026}
}
```

## Authors

- Beatriz Royo, Fundación Zaragoza Logistics Center (ZLC)
- María Teresa de la Cruz, Fundación Zaragoza Logistics Center (ZLC)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
