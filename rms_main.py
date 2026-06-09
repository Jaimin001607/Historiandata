import logging

from alerting_system import AlertingSystem
from training_pipeline import RMSTrainingPipeline


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    historian_files = [
        r"c:\Users\jaiminsuthar\Downloads\CSA Reliability data Feb2025 to now.csv",
        r"c:\Users\jaiminsuthar\Downloads\CSA Reliability data Jan2026(6 months).csv",
        r"c:\Users\jaiminsuthar\Downloads\CSA Reliability data Jan 2026(2nd location).csv",
        r"c:\Users\jaiminsuthar\Downloads\CSA Reliability data Jan 2026 to now(all america).csv",
        r"c:\Users\jaiminsuthar\Downloads\CSA Reliability data Jan 2025 to now(all america).csv",
    ]

    pipeline = RMSTrainingPipeline(output_dir='trained_models')
    consolidated_data = pipeline.load_and_consolidate(historian_files)

    print(f"Loaded {len(consolidated_data)} records across {consolidated_data['component_id'].nunique()} components")

    training_files = pipeline.export_sensor_training_files(consolidated_data, output_dir='sensor_training_data')
    print(f"Exported {len(training_files)} sensor training files")

    models_by_file = pipeline.train_models_by_file(historian_files, min_samples=30)
    print(f"Trained {len(models_by_file)} baseline models from per-file historian data")

    models_by_sensor = pipeline.train_sensor_models(consolidated_data, min_samples=30)
    print(f"Trained {len(models_by_sensor)} per-sensor models from consolidated data")

    saved_path = pipeline.save_models(save_dir='trained_models')
    print(f"Saved trained models to {saved_path}")

    alerting = AlertingSystem(log_file='rms_alerts.log')
    sample_key = next(iter(models_by_sensor), None)
    if sample_key is not None:
        sample_model = pipeline.get_model(sample_key)
        latest_data = consolidated_data[consolidated_data['component_id'] == sample_model.component_id].tail(10)
        analyzed = sample_model.analyze(latest_data)
        detections = sample_model.detect_deviation(analyzed)
        alerts = alerting.process_detections([detections])
        print(alerting.format_output([detections], alerts))

    # Interactive plotting prompt
    try:
        ans = input("Would you like to plot a sensor now? [y/N]: ").strip().lower()
    except Exception:
        ans = 'n'

    if ans in ('y', 'yes'):
        comps = list(consolidated_data['component_id'].unique())
        print("Available components:")
        for i, c in enumerate(comps):
            print(f"{i}: {c}")

        try:
            sel = input(f"Choose component index (0-{len(comps)-1}) [0]: ").strip()
            comp_idx = int(sel) if sel else 0
            comp = comps[comp_idx]
        except Exception:
            print("Invalid selection — using first component")
            comp = comps[0]

        sensors = pipeline.client.get_sensor_columns(consolidated_data[consolidated_data['component_id'] == comp])
        if not sensors:
            print(f"No sensors found for component {comp}")
        else:
            print("Available sensors:")
            for i, s in enumerate(sensors):
                print(f"{i}: {s}")

            try:
                sel = input(f"Choose sensor index (0-{len(sensors)-1}) [0]: ").strip()
                sensor_idx = int(sel) if sel else 0
                sensor = sensors[sensor_idx]
            except Exception:
                print("Invalid selection — using first sensor")
                sensor = sensors[0]

            last_days = None
            try:
                ld = input("Enter last_days to plot (e.g., 365) or press Enter for all: ").strip()
                last_days = int(ld) if ld else None
            except Exception:
                last_days = None

            ov = input("Overlay trained baseline if available? [Y/n]: ").strip().lower()
            overlay = (ov not in ('n', 'no'))

            png = pipeline.plot_sensor(consolidated_data, component_id=comp, sensor=sensor, last_days=last_days, show=True, overlay_baseline=overlay)
            if png:
                print(f"Saved plot: {png}")


if __name__ == '__main__':
    main()
