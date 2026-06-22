QUTIP_PATH=$(python3 -c "import os, qutip; print(os.path.dirname(os.path.dirname(qutip.__file__)))")

#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/fluorescence_check.py --device-db device_db_sim.py
#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/rabi_flop.py --device-db device_db_sim.py
#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/ramsey_spectroscopy.py --device-db device_db_sim.py
#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/sideband_spectroscopy.py --device-db device_db_sim.py
#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/sideband_cooling.py --device-db device_db_sim.py
#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/shuttling.py --device-db device_db_sim.py
#PYTHONPATH=.:$QUTIP_PATH artiq_run experiments/ms_gate.py --device-db device_db_sim.py
PYTHONPATH=.:$QUTIP_PATH artiq_run sim_checks/qec_x_check.py --device-db device_db_sim.py
