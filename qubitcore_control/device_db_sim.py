from dax.sim import enable_dax_sim

device_db = enable_dax_sim(enable=True, ddb={
    "core": {
        "type": "local",
        "module": "sim.core",
        "class": "SimCore",
        "arguments": {}
    },

    "ttl_pmt": {
        "type": "local",
        "module": "sim.devices",
        "class": "SimPMT",
        "arguments": {}
    },

    "dds_729": {
        "type": "local",
        "module": "sim.devices",
        "class": "SimDDS729",
        "arguments": {}
    }
})