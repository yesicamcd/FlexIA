import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from shared.container import (
    get_create_session_use_case,
    get_process_video_use_case,
    get_session_results_use_case,
    get_create_patient_use_case,
    get_patient_history_use_case,
    get_session_repository,
    get_patient_repository,
)

print('Todos los use cases disponibles')

history_uc = get_patient_history_use_case()
history = history_uc.execute('2146ff2d-4c96-42b1-9818-64e3119709ab')
print('Sesiones de Juanito:', len(history))
for s in history:
    print(' ', s['session_date'][:10], s['status'], s['ifi_score'], s['routine_name'])

results_uc = get_session_results_use_case()
result = results_uc.execute('1984ec5c-c61b-40f1-bc74-7dfa2270c47e')
if result:
    print('Sesion:', result.status, '| IFI:', result.ifi_score)
    for ex in result.exercise_results:
        print(' ', ex.exercise_name, ex.rom_percentage, ex.performance)
