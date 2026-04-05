// Weight Assistant - Frontend Application

const API = '';
const today = () => new Date().toISOString().split('T')[0];

// --- Navigation ---
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
});

// --- Utility ---
async function api(path, options = {}) {
    const resp = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    return resp.json();
}

function showMsg(id, text, type = 'info') {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = text;
        el.className = `msg ${type}`;
        setTimeout(() => { el.textContent = ''; }, 5000);
    }
}

function setDefaults() {
    document.getElementById('w-date').value = today();
    document.getElementById('wo-date').value = today();
    document.getElementById('ml-date').value = today();
    document.getElementById('menu-date').value = today();
}

// --- Status ---
async function checkStatus() {
    try {
        const data = await api('/api/status');
        const el = document.getElementById('ollama-status');
        if (data.ollama_available) {
            el.innerHTML = `<span class="ok">Ollama connected</span> (${data.ollama_models.length} models)`;
        } else {
            el.innerHTML = '<span class="err">Ollama unavailable</span> - workout interpretation and explanations will use fallbacks';
        }
    } catch {
        document.getElementById('ollama-status').innerHTML = '<span class="err">Backend unreachable</span>';
    }
}

// --- Profile ---
async function loadProfile() {
    try {
        const data = await api('/api/profile');
        if (data && data.age) {
            document.getElementById('prof-age').value = data.age;
            document.getElementById('prof-height').value = data.height_cm;
            document.getElementById('prof-weight').value = data.weight_kg;
            document.getElementById('prof-target').value = data.target_weight_kg;
            document.getElementById('prof-sex').value = data.sex;
            document.getElementById('prof-activity').value = data.activity_level;
            return data;
        }
    } catch { }
    return null;
}

document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        age: parseInt(document.getElementById('prof-age').value),
        height_cm: parseFloat(document.getElementById('prof-height').value),
        weight_kg: parseFloat(document.getElementById('prof-weight').value),
        target_weight_kg: parseFloat(document.getElementById('prof-target').value),
        sex: document.getElementById('prof-sex').value,
        activity_level: document.getElementById('prof-activity').value,
    };
    try {
        await api('/api/profile', { method: 'PUT', body: JSON.stringify(body) });
        showMsg('profile-msg', 'Profile saved!', 'success');
        loadDashboard();
    } catch {
        showMsg('profile-msg', 'Error saving profile', 'error');
    }
});

// --- Weight ---
async function loadWeightHistory() {
    try {
        const data = await api('/api/weight?limit=30');
        const tbody = document.querySelector('#weight-table tbody');
        tbody.innerHTML = '';
        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="3" class="muted">No weight entries yet</td></tr>';
        }
        data.forEach(w => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${w.date}</td><td>${w.weight_kg}</td><td><button class="btn-danger" onclick="deleteWeight(${w.id})">Delete</button></td>`;
            tbody.appendChild(tr);
        });
        renderWeightChart(data);
        return data;
    } catch { return []; }
}

function renderWeightChart(data) {
    const container = document.getElementById('weight-chart');
    if (!data.length) {
        container.innerHTML = '<p class="muted">No weight data to display</p>';
        return;
    }
    const sorted = [...data].reverse();
    const min = Math.min(...sorted.map(w => w.weight_kg));
    const max = Math.max(...sorted.map(w => w.weight_kg));
    const range = max - min || 1;

    let html = '<div class="weight-bars">';
    sorted.forEach(w => {
        const h = 20 + ((w.weight_kg - min) / range) * 80;
        html += `<div class="weight-bar" style="height:${h}%" data-label="${w.date}: ${w.weight_kg}kg"></div>`;
    });
    html += '</div>';
    html += `<div style="display:flex;justify-content:space-between;font-size:0.7rem;color:var(--text-muted);margin-top:0.3rem"><span>${sorted[0]?.date || ''}</span><span>${sorted[sorted.length-1]?.date || ''}</span></div>`;
    container.innerHTML = html;
}

document.getElementById('weight-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        date: document.getElementById('w-date').value,
        weight_kg: parseFloat(document.getElementById('w-kg').value),
    };
    try {
        await api('/api/weight', { method: 'POST', body: JSON.stringify(body) });
        showMsg('weight-msg', 'Weight entry added!', 'success');
        loadWeightHistory();
        loadDashboard();
    } catch {
        showMsg('weight-msg', 'Error saving weight', 'error');
    }
});

window.deleteWeight = async function(id) {
    if (!confirm('Delete this weight entry?')) return;
    await api(`/api/weight/${id}`, { method: 'DELETE' });
    loadWeightHistory();
};

// --- Menu ---
document.getElementById('btn-fetch-menu').addEventListener('click', async () => {
    const dateVal = document.getElementById('menu-date').value || today();
    const display = document.getElementById('menu-display');
    display.innerHTML = '<span class="loading"></span> Fetching menu...';

    try {
        const data = await api(`/api/menu/fetch?target_date=${dateVal}`);
        if (data.status === 'ok') {
            showMsg('menu-msg', `Menu fetched: ${data.items_count} items`, 'success');
            loadMenuDisplay(dateVal);
        } else {
            display.innerHTML = `<p class="muted">${data.message || 'Could not fetch menu'}</p>`;
            showMsg('menu-msg', data.message || 'Error', 'error');
        }
    } catch {
        display.innerHTML = '<p class="muted">Error fetching menu. Is the menu API running?</p>';
        showMsg('menu-msg', 'Failed to fetch menu', 'error');
    }
});

async function loadMenuDisplay(dateStr) {
    const d = dateStr || today();
    try {
        const data = await api(`/api/menu/today?target_date=${d}`);
        const display = document.getElementById('menu-display');
        if (data.status !== 'ok' || !data.items?.length) {
            display.innerHTML = '<p class="muted">No menu for this date.</p>';
            return data;
        }

        const cats = {};
        data.items.forEach(item => {
            const cat = item.category || 'Other';
            if (!cats[cat]) cats[cat] = [];
            cats[cat].push(item);
        });

        let html = '';
        for (const [cat, items] of Object.entries(cats)) {
            html += `<div class="menu-category"><h4>${cat}</h4>`;
            items.forEach(item => {
                const cal = item.estimated_calories ? `~${item.estimated_calories} kcal` : 'unknown cal';
                html += `<div class="menu-item"><span>${item.dish_name || item.name}</span><span class="cal">${cal}</span></div>`;
            });
            html += '</div>';
        }
        display.innerHTML = html;
        return data;
    } catch {
        return null;
    }
}

// --- Workout ---
document.getElementById('workout-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    const body = {
        date: document.getElementById('wo-date').value,
        raw_text: document.getElementById('wo-text').value,
        duration_minutes: parseInt(document.getElementById('wo-duration').value) || 0,
        intensity: document.getElementById('wo-intensity').value || null,
        steps: parseInt(document.getElementById('wo-steps').value) || null,
    };

    try {
        const data = await api('/api/workout', { method: 'POST', body: JSON.stringify(body) });
        if (data.status === 'ok') {
            showMsg('workout-msg', `Workout logged: ${data.workout_type} — ~${data.estimated_calories_burned} kcal burned`, 'success');
            document.getElementById('wo-text').value = '';
            document.getElementById('wo-duration').value = '0';
            document.getElementById('wo-intensity').value = '';
            document.getElementById('wo-steps').value = '';
            loadWorkouts();
            loadDashboard();
        } else {
            showMsg('workout-msg', 'Error logging workout', 'error');
        }
    } catch {
        showMsg('workout-msg', 'Error logging workout', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Log Workout';
    }
});

async function loadWorkouts() {
    try {
        const data = await api('/api/workout?limit=10');
        const container = document.getElementById('workout-list');
        if (!data.length) {
            container.innerHTML = '<p class="muted">No workouts logged yet</p>';
            return;
        }
        container.innerHTML = data.map(w => `
            <div class="workout-card">
                <div class="workout-info">
                    <span class="type">${w.workout_type || 'General'}</span>
                    <div class="details">${w.date} — ${w.duration_minutes || 0} min${w.intensity ? ' / ' + w.intensity : ''}${w.steps ? ' / ' + w.steps + ' steps' : ''}</div>
                    ${w.raw_text ? `<div class="details">${w.raw_text}</div>` : ''}
                </div>
                <span class="cal-badge">${w.estimated_calories_burned || 0} kcal</span>
                <button class="btn-danger" onclick="deleteWorkout(${w.id})" style="margin-left:0.5rem">Delete</button>
            </div>
        `).join('');
    } catch { }
}

window.deleteWorkout = async function(id) {
    if (!confirm('Delete this workout?')) return;
    await api(`/api/workout/${id}`, { method: 'DELETE' });
    loadWorkouts();
    loadDashboard();
};

// --- Meal Log ---
document.getElementById('meal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        date: document.getElementById('ml-date').value,
        dishes: document.getElementById('ml-dishes').value,
        second_serving: document.getElementById('ml-second').checked,
        bread: document.getElementById('ml-bread').checked,
        notes: document.getElementById('ml-notes').value || null,
    };

    try {
        const data = await api('/api/meals', { method: 'POST', body: JSON.stringify(body) });
        if (data.status === 'ok') {
            const calText = data.total_estimated_calories ? ` (~${data.total_estimated_calories} kcal)` : '';
            showMsg('meal-msg', `Meal logged${calText}`, 'success');
            document.getElementById('ml-dishes').value = '';
            document.getElementById('ml-second').checked = false;
            document.getElementById('ml-bread').checked = false;
            document.getElementById('ml-notes').value = '';
            loadMealLogs();
            loadDashboard();
        }
    } catch {
        showMsg('meal-msg', 'Error logging meal', 'error');
    }
});

async function loadMealLogs() {
    try {
        const data = await api('/api/meals?limit=10');
        const container = document.getElementById('meal-list');
        if (!data.length) {
            container.innerHTML = '<p class="muted">No meals logged yet</p>';
            return;
        }
        container.innerHTML = data.map(m => `
            <div class="meal-card">
                <div class="meal-info">
                    <strong>${m.date}</strong>
                    <div class="details">${m.dishes}${m.bread ? ' + bread' : ''}${m.second_serving ? ' + 2nd serving' : ''}</div>
                    ${m.notes ? `<div class="details">${m.notes}</div>` : ''}
                </div>
                ${m.total_estimated_calories ? `<span class="cal-badge">${m.total_estimated_calories} kcal</span>` : ''}
                <button class="btn-danger" onclick="deleteMeal(${m.id})" style="margin-left:0.5rem">Delete</button>
            </div>
        `).join('');
    } catch { }
}

window.deleteMeal = async function(id) {
    if (!confirm('Delete this meal log?')) return;
    await api(`/api/meals/${id}`, { method: 'DELETE' });
    loadMealLogs();
    loadDashboard();
};

// --- Dish Catalog ---
async function loadDishCatalog(search = '') {
    try {
        const q = search ? `?search=${encodeURIComponent(search)}` : '';
        const data = await api(`/api/dishes${q}`);
        const tbody = document.querySelector('#dish-table tbody');
        tbody.innerHTML = '';
        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="muted">No dishes found</td></tr>';
            return;
        }
        data.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${d.normalized_name}</td>
                <td>${d.estimated_calories_per_serving} kcal</td>
                <td>${d.category || '-'}</td>
                <td>${d.confidence || '-'}</td>
                <td><button class="btn-danger" onclick="deleteDish(${d.id})">Delete</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch { }
}

document.getElementById('dish-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        normalized_name: document.getElementById('dc-name').value,
        estimated_calories_per_serving: parseInt(document.getElementById('dc-cal').value),
        category: document.getElementById('dc-cat').value,
        confidence: 'known',
    };
    try {
        await api('/api/dishes', { method: 'POST', body: JSON.stringify(body) });
        showMsg('dish-msg', 'Dish saved!', 'success');
        document.getElementById('dc-name').value = '';
        document.getElementById('dc-cal').value = '';
        loadDishCatalog();
    } catch {
        showMsg('dish-msg', 'Error saving dish', 'error');
    }
});

document.getElementById('dc-search').addEventListener('input', (e) => {
    loadDishCatalog(e.target.value);
});

window.deleteDish = async function(id) {
    if (!confirm('Delete this dish from catalog?')) return;
    await api(`/api/dishes/${id}`, { method: 'DELETE' });
    loadDishCatalog();
};

// --- Dashboard ---
async function loadDashboard() {
    const d = today();

    // Profile summary
    const profile = await loadProfile();
    const profEl = document.getElementById('dash-profile-content');
    if (profile && profile.age) {
        const diff = (profile.weight_kg - profile.target_weight_kg).toFixed(1);
        const goal = diff > 1 ? 'lose' : diff < -1 ? 'gain' : 'maintain';
        profEl.innerHTML = `
            <div class="stats-row">
                <div class="stat"><div class="value">${profile.weight_kg}</div><div class="label">Current kg</div></div>
                <div class="stat"><div class="value">${profile.target_weight_kg}</div><div class="label">Target kg</div></div>
                <div class="stat"><div class="value">${Math.abs(diff)}</div><div class="label">kg to ${goal}</div></div>
            </div>
            <p class="muted" style="margin-top:0.5rem">${profile.sex}, ${profile.age}y, ${profile.height_cm}cm, ${profile.activity_level} activity</p>
        `;
    } else {
        profEl.innerHTML = '<p class="muted">No profile set. Go to Profile tab to set up.</p>';
    }

    // Weight trend
    const weights = await loadWeightHistory();
    const weightEl = document.getElementById('dash-weight-content');
    if (weights.length) {
        const latest = weights[0];
        const weekAgo = weights.find(w => {
            const d1 = new Date(latest.date);
            const d2 = new Date(w.date);
            return (d1 - d2) / 86400000 >= 6;
        });
        let trend = '';
        if (weekAgo) {
            const diff = (latest.weight_kg - weekAgo.weight_kg).toFixed(1);
            trend = diff > 0 ? `+${diff} kg this week` : `${diff} kg this week`;
        }
        weightEl.innerHTML = `
            <div class="stats-row">
                <div class="stat"><div class="value">${latest.weight_kg}</div><div class="label">Latest (${latest.date})</div></div>
                ${trend ? `<div class="stat"><div class="value">${trend}</div><div class="label">Weekly trend</div></div>` : ''}
            </div>
        `;
    } else {
        weightEl.innerHTML = '<p class="muted">No weight entries. Go to Weight tab to add.</p>';
    }

    // Today's activity
    try {
        const activities = await api(`/api/workout?target_date=${d}`);
        const actEl = document.getElementById('dash-activity-content');
        if (activities.length) {
            const totalCal = activities.reduce((s, a) => s + (a.estimated_calories_burned || 0), 0);
            actEl.innerHTML = `
                <div class="stats-row">
                    <div class="stat"><div class="value">${totalCal}</div><div class="label">kcal burned</div></div>
                    <div class="stat"><div class="value">${activities.length}</div><div class="label">activities</div></div>
                </div>
                ${activities.map(a => `<p class="muted" style="margin-top:0.3rem">${a.workout_type} — ${a.duration_minutes}min${a.steps ? ', ' + a.steps + ' steps' : ''}</p>`).join('')}
            `;
        } else {
            actEl.innerHTML = '<p class="muted">No activity logged today</p>';
        }
    } catch { }

    // Today's menu
    const menuData = await loadMenuDisplay(d);
    const dashMenuEl = document.getElementById('dash-menu-content');
    if (menuData && menuData.status === 'ok' && menuData.items?.length) {
        const items = menuData.items.map(i => i.dish_name || i.name).join(', ');
        dashMenuEl.innerHTML = `<p>${items}</p>`;
    } else {
        dashMenuEl.innerHTML = '<p class="muted">No menu loaded for today</p>';
    }

    // Today's meals
    try {
        const meals = await api(`/api/meals?target_date=${d}`);
        const mealsEl = document.getElementById('dash-meals-content');
        if (meals.length) {
            const totalCal = meals.reduce((s, m) => s + (m.total_estimated_calories || 0), 0);
            mealsEl.innerHTML = meals.map(m =>
                `<p>${m.dishes}${m.bread ? ' + bread' : ''}${m.second_serving ? ' + 2nd serving' : ''} ${m.total_estimated_calories ? `(~${m.total_estimated_calories} kcal)` : ''}</p>`
            ).join('') + (totalCal ? `<p style="margin-top:0.3rem"><strong>Total: ~${totalCal} kcal</strong></p>` : '');
        } else {
            mealsEl.innerHTML = '<p class="muted">No meals logged today</p>';
        }
    } catch { }

    // Recommendation
    loadRecommendation(d);
}

async function loadRecommendation(dateStr) {
    const recEl = document.getElementById('dash-rec-content');
    // Check prerequisites
    const profile = await api('/api/profile');
    if (!profile || !profile.age) {
        recEl.innerHTML = '<p class="muted">Set up your profile first to get recommendations.</p>';
        return;
    }

    const menu = await api(`/api/menu/today?target_date=${dateStr}`);
    if (!menu || menu.status !== 'ok' || !menu.items?.length) {
        recEl.innerHTML = '<p class="muted">Load today\'s menu first to get recommendations.</p>';
        return;
    }

    recEl.innerHTML = '<span class="loading"></span> Generating recommendation...';

    try {
        const rec = await api(`/api/recommendation?target_date=${dateStr}`);
        if (rec.status !== 'ok') {
            recEl.innerHTML = `<p class="muted">${rec.message || 'Could not generate recommendation'}</p>`;
            return;
        }

        recEl.innerHTML = `
            <div class="rec-section">
                <strong>Calorie Budget</strong>
                <div class="stats-row">
                    <div class="stat"><div class="value">${rec.calorie_target}</div><div class="label">Daily target</div></div>
                    <div class="stat"><div class="value">${rec.activity_calories}</div><div class="label">Activity bonus</div></div>
                    <div class="stat"><div class="value">${rec.meal_calorie_budget}</div><div class="label">Lunch budget</div></div>
                </div>
            </div>
            <div class="rec-section">
                <strong>Recommended Meal</strong>
                <div class="rec-dishes">
                    ${(rec.recommended_dishes || []).map(d => `<span class="rec-dish">${d}</span>`).join('')}
                </div>
                <div style="margin-top:0.4rem">
                    Bread: <span class="rec-badge ${rec.bread_recommended ? 'yes' : 'no'}">${rec.bread_recommended ? 'OK' : 'Skip'}</span>
                    Second serving: <span class="rec-badge ${rec.second_serving_recommended ? 'yes' : 'no'}">${rec.second_serving_recommended ? 'OK' : 'Skip'}</span>
                </div>
                <div style="margin-top:0.3rem;font-size:0.85rem;color:var(--text-muted)">~${rec.recommended_calories} kcal estimated</div>
            </div>
            ${rec.lighter_alternative?.dishes?.length ? `
            <div class="rec-section">
                <strong>Lighter Option</strong>
                <div class="rec-dishes">${rec.lighter_alternative.dishes.map(d => `<span class="rec-dish">${d}</span>`).join('')}</div>
                <div style="font-size:0.8rem;color:var(--text-muted)">~${rec.lighter_alternative.estimated_calories} kcal</div>
            </div>` : ''}
            ${rec.more_filling_alternative?.dishes?.length ? `
            <div class="rec-section">
                <strong>More Filling Option</strong>
                <div class="rec-dishes">${rec.more_filling_alternative.dishes.map(d => `<span class="rec-dish">${d}</span>`).join('')}</div>
                <div style="font-size:0.8rem;color:var(--text-muted)">~${rec.more_filling_alternative.estimated_calories} kcal${rec.more_filling_alternative.bread ? ' + bread' : ''}</div>
            </div>` : ''}
            ${rec.explanation ? `<div class="rec-explanation">${rec.explanation}</div>` : ''}
            <p class="muted" style="margin-top:0.5rem;font-size:0.75rem">All calorie values are estimates. This is not medical advice.</p>
        `;
    } catch (err) {
        recEl.innerHTML = '<p class="muted">Error generating recommendation. Check that your profile and menu are set up.</p>';
    }
}

// --- Init ---
setDefaults();
checkStatus();
loadProfile();
loadDashboard();
loadWorkouts();
loadMealLogs();
loadDishCatalog();
