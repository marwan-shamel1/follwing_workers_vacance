/* ==========================================================================
   Egyptian Military Leaves Management System - Interactive Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss flash messages after 6 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 6000);
    });

    // 2. Date calculation logic: automatically calculate days_count
    function setupDateCalculation(startId, endId, daysId) {
        const startInput = document.getElementById(startId);
        const endInput = document.getElementById(endId);
        const daysInput = document.getElementById(daysId);

        if (!startInput || !endInput || !daysInput) return;

        function calculateDiff() {
            if (startInput.value && endInput.value) {
                const s = new Date(startInput.value);
                const e = new Date(endInput.value);
                if (e >= s) {
                    const diffTime = Math.abs(e - s);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // inclusive of end date
                    daysInput.value = diffDays;
                } else {
                    daysInput.value = 1;
                }
            }
        }

        startInput.addEventListener('change', function () {
            if (!endInput.value || new Date(endInput.value) < new Date(startInput.value)) {
                endInput.value = startInput.value;
            }
            calculateDiff();
        });

        endInput.addEventListener('change', calculateDiff);
    }

    setupDateCalculation('id_start_date', 'id_end_date', 'id_days_count');
    setupDateCalculation('mgr_start_date', 'mgr_end_date', 'mgr_days_count');

    // 3. Permission Hours toggle based on leave type
    function setupPermissionToggle(typeSelectId, hoursGroupId) {
        const typeSelect = document.getElementById(typeSelectId);
        const hoursGroup = document.getElementById(hoursGroupId);

        if (!typeSelect || !hoursGroup) return;

        function toggleHours() {
            if (typeSelect.value === 'permission') {
                hoursGroup.style.display = 'block';
            } else {
                hoursGroup.style.display = 'none';
            }
        }

        typeSelect.addEventListener('change', toggleHours);
        toggleHours(); // initial state
    }

    setupPermissionToggle('id_leave_type', 'group_permission_hours');
    setupPermissionToggle('mgr_leave_type', 'group_mgr_permission_hours');

    // 4. Worker Portal: Live Dropdown change handler
    const workerSelect = document.getElementById('workerSelectDropdown');
    if (workerSelect) {
        workerSelect.addEventListener('change', function () {
            const workerId = this.value;
            if (!workerId) {
                resetWorkerData();
                return;
            }
            loadWorkerSummary(workerId);
        });

        // Trigger on load if initial value exists
        if (workerSelect.value) {
            loadWorkerSummary(workerSelect.value);
        }
    }

    function loadWorkerSummary(workerId) {
        const loader = document.getElementById('workerDataLoader');
        if (loader) loader.style.display = 'block';

        fetch(`/api/worker/${workerId}/summary/`)
            .then(response => {
                if (!response.ok) throw new Error('Network error');
                return response.json();
            })
            .then(data => {
                if (loader) loader.style.display = 'none';
                if (data.status === 'success') {
                    updateWorkerUI(data.worker, data.summary, data.leaves);
                }
            })
            .catch(err => {
                if (loader) loader.style.display = 'none';
                console.error('Error fetching worker data:', err);
            });
    }

    function updateWorkerUI(worker, summary, leaves) {
        // Form hidden & visible inputs
        const workerIdHidden = document.getElementById('hidden_worker_id');
        if (workerIdHidden) workerIdHidden.value = worker.id;

        const nameInput = document.getElementById('id_applicant_name');
        if (nameInput) nameInput.value = worker.name;

        const jobInput = document.getElementById('id_applicant_job');
        if (jobInput) jobInput.value = worker.job_title;

        const deptInput = document.getElementById('id_applicant_department');
        if (deptInput) deptInput.value = worker.department;

        const phoneInput = document.getElementById('id_applicant_phone');
        if (phoneInput && !phoneInput.value) phoneInput.value = worker.phone || '';

        // Header info cards
        const dispName = document.getElementById('disp_worker_name');
        if (dispName) dispName.textContent = worker.name;

        const dispJob = document.getElementById('disp_worker_job');
        if (dispJob) dispJob.textContent = worker.job_title;

        const dispDept = document.getElementById('disp_worker_dept');
        if (dispDept) dispDept.textContent = worker.department;

        const dispId = document.getElementById('disp_worker_nid');
        if (dispId) dispId.textContent = worker.national_id;

        // Tally updates
        setMetric('val_reg_taken', summary.regular.taken);
        setMetric('val_reg_rem', summary.regular.remaining);
        
        setMetric('val_cas_taken', summary.casual.taken);
        setMetric('val_cas_rem', summary.casual.remaining);
        
        setMetric('val_perm_taken', summary.permission.taken);
        setMetric('val_perm_rem', summary.permission.remaining);

        setMetric('val_hosp_taken', summary.hospital.taken);
        setMetric('val_sick_taken', summary.sick.taken);
        setMetric('val_miss_taken', summary.mission.taken);

        // Leaves History Table
        const tbody = document.getElementById('workerLeavesTableBody');
        const emptyState = document.getElementById('workerLeavesEmptyState');

        if (tbody) {
            tbody.innerHTML = '';
            if (leaves && leaves.length > 0) {
                if (emptyState) emptyState.style.display = 'none';
                leaves.forEach(l => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><span class="badge badge-${l.composite_status.badge_class || 'info'}"><i class="fa ${l.composite_status.icon}"></i> ${l.composite_status.label}</span></td>
                        <td><strong>${l.leave_type_display}</strong></td>
                        <td>${l.days_count} يوم ${l.permission_hours ? `(${l.permission_hours})` : ''}</td>
                        <td>${l.start_date}</td>
                        <td>${l.end_date}</td>
                        <td><small class="text-muted">${l.created_at}</small></td>
                        <td>
                            ${l.can_print ? `<a href="/leaves/print/${l.id}/" target="_blank" class="btn btn-sm btn-outline"><i class="fa fa-print"></i> أمر إجازة</a>` : '<span class="text-muted">-</span>'}
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                if (emptyState) emptyState.style.display = 'block';
            }
        }

        // Show sections
        const dataSection = document.getElementById('workerDetailSection');
        if (dataSection) dataSection.style.display = 'block';
    }

    function setMetric(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function resetWorkerData() {
        const dataSection = document.getElementById('workerDetailSection');
        if (dataSection) dataSection.style.display = 'none';
    }

    // 5. Commander Live Search Engine
    const searchInput = document.getElementById('commanderLiveSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const query = this.value.trim().toLowerCase();
            const workerCards = document.querySelectorAll('.commander-worker-card');
            let visibleCount = 0;

            workerCards.forEach(card => {
                const searchData = card.getAttribute('data-search') || '';
                if (searchData.toLowerCase().includes(query)) {
                    card.style.display = '';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            const countEl = document.getElementById('matchingWorkersCount');
            if (countEl) countEl.textContent = visibleCount;

            const noResults = document.getElementById('noSearchResults');
            if (noResults) {
                noResults.style.display = visibleCount === 0 ? 'block' : 'none';
            }
        });
    }

    // 6. Generic Modal Open/Close
    window.openModal = function (modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('show');
    };

    window.closeModal = function (modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('show');
    };

    // Close when clicking outside dialog
    document.querySelectorAll('.mil-modal').forEach(m => {
        m.addEventListener('click', function (e) {
            if (e.target === this) {
                this.classList.remove('show');
            }
        });
    });
});
