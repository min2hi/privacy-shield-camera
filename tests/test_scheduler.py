from app.core.frame_scheduler import FrameScheduler


def test_scheduler_detects_at_declared_cadence():
    scheduler = FrameScheduler(enabled=True, skip_ratio=2)
    decisions = []
    for frame_index in range(6):
        decisions.append(scheduler.should_detect())
        if decisions[-1]:
            scheduler.update_detections([{"frame": frame_index}])
        else:
            scheduler.skip_frame()

    assert decisions == [True, False, True, False, True, False]
    assert scheduler.get_last_detections() == [{"frame": 4}]


def test_disabled_scheduler_detects_every_frame():
    scheduler = FrameScheduler(enabled=False, skip_ratio=99)
    assert all(scheduler.should_detect() for _ in range(3))


def test_reset_drops_cache_and_restarts_cadence():
    scheduler = FrameScheduler(enabled=True, skip_ratio=2)
    scheduler.update_detections([{"frame": 0}])
    scheduler.reset()
    assert scheduler.frame_counter == 0
    assert scheduler.get_last_detections() == []
    assert scheduler.should_detect()
