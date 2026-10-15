import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "FactoryTwin Simulation Platform"
    assert "default_simulation_id" in data


def test_get_scenarios(client):
    response = client.get("/api/simulations/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 1
    assert scenarios[0]["id"] == "default_factory"


def test_simulation_lifecycle(client):
    # 1. Create simulation
    create_res = client.post("/api/simulations", json={
        "scheduling_policy": "NEAREST_ROBOT",
        "num_robots": 2,
    })
    assert create_res.status_code == 200
    sim_data = create_res.json()
    sim_id = sim_data["simulation_id"]
    assert sim_data["robots_count"] == 2

    # 2. Step simulation
    step_res = client.post(f"/api/simulations/{sim_id}/step")
    assert step_res.status_code == 200
    assert step_res.json()["tick"] == 1

    # 3. Add task
    task_res = client.post(f"/api/simulations/{sim_id}/tasks", json={
        "pickup_x": 1,
        "pickup_y": 2,
        "dest_x": 9,
        "dest_y": 3,
        "priority": "HIGH",
        "item_type": "Bearing Cap",
    })
    assert task_res.status_code == 200
    assert "task_id" in task_res.json()

    # 4. Add dynamic obstacle
    obs_res = client.post(f"/api/simulations/{sim_id}/obstacles", json={
        "x": 5,
        "y": 5,
    })
    assert obs_res.status_code == 200
    obs_id = obs_res.json()["obstacle_id"]

    # 5. Remove obstacle
    del_res = client.delete(f"/api/simulations/{sim_id}/obstacles/{obs_id}")
    assert del_res.status_code == 200

    # 6. Reset simulation
    reset_res = client.post(f"/api/simulations/{sim_id}/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["tick"] == 0


def test_inspection_api(client):
    # Get samples
    samples_res = client.get("/api/inspection/samples")
    assert samples_res.status_code == 200
    samples = samples_res.json()
    assert len(samples) > 0

    first_sample = samples[0]
    analyze_res = client.post(f"/api/inspection/analyze?sample_id={first_sample['id']}")
    assert analyze_res.status_code == 200
    analysis = analyze_res.json()
    assert analysis["prediction"] in ("ACCEPTABLE", "SUSPECTED DEFECT", "INCONCLUSIVE")
    assert "annotated_image_b64" in analysis

    # Metrics endpoint
    metrics_res = client.get("/api/inspection/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_evaluated"] > 0


def test_benchmark_api(client):
    bm_res = client.post("/api/benchmarks/run", json={
        "num_robots": 2,
        "num_tasks": 3,
        "max_ticks": 40,
        "seed": 123,
    })
    assert bm_res.status_code == 200
    data = bm_res.json()
    assert len(data["trials"]) == 2
    assert "comparison" in data
    assert data["trials"][0]["actual_collisions"] == 0
    assert data["trials"][1]["actual_collisions"] == 0
