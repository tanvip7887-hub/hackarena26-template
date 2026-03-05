import time

LOITER_THRESHOLD_SECONDS = 30

class LoiterTracker:
    def __init__(self, threshold=LOITER_THRESHOLD_SECONDS):
        self.threshold = threshold
        # {person_id: entry_timestamp}
        self._entry_times = {}

    def person_entered(self, person_id):
        if person_id not in self._entry_times:
            self._entry_times[person_id] = time.time()

    def person_exited(self, person_id):
        self._entry_times.pop(person_id, None)

    def get_loiter_time(self, person_id):
        if person_id not in self._entry_times:
            return 0.0
        return time.time() - self._entry_times[person_id]

    def is_loitering(self, person_id):
        return self.get_loiter_time(person_id) >= self.threshold

    def cleanup_absent(self, active_ids):
        inactive = [pid for pid in self._entry_times if pid not in active_ids]
        for pid in inactive:
            del self._entry_times[pid]

    def all_entry_times(self):
        return dict(self._entry_times)