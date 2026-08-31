(() => {
	const { createApp, ref, computed, onMounted, watch } = Vue;
	const METHOD = "numerouno.numerouno.api.training_schedule";

	function csrf() {
		return document.querySelector('meta[name="csrf-token"]')?.content || "";
	}

	async function call(method, args = {}) {
		const payload = {};
		Object.entries(args).forEach(([key, value]) => {
			if (value !== null && value !== undefined) {
				payload[key] = value;
			}
		});
		const res = await fetch(`/api/method/${METHOD}.${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
				"X-Frappe-CSRF-Token": csrf(),
			},
			credentials: "same-origin",
			body: JSON.stringify(payload),
		});
		const data = await res.json();
		if (!res.ok || data.exc) {
			let message = "Request failed";
			try {
				if (data._server_messages) {
					const msgs = JSON.parse(data._server_messages);
					message = JSON.parse(msgs[0]).message || message;
				} else if (data.exception) {
					message = String(data.exception).replace(/<[^>]+>/g, " ");
				}
			} catch (e) {
				message = data.exception || message;
			}
			throw new Error(message);
		}
		return data.message;
	}

	function ymd(d) {
		const y = d.getFullYear();
		const m = String(d.getMonth() + 1).padStart(2, "0");
		const day = String(d.getDate()).padStart(2, "0");
		return `${y}-${m}-${day}`;
	}

	function formatWeek(start, end) {
		if (!start) return "";
		const a = new Date(start + "T00:00:00");
		const b = new Date((end || start) + "T00:00:00");
		if (start === end) {
			return a.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
		}
		const opts = { month: "short", day: "numeric" };
		return `${a.toLocaleDateString(undefined, opts)} – ${b.toLocaleDateString(undefined, { ...opts, year: "numeric" })}`;
	}

	function initials(name) {
		return (name || "?")
			.split(" ")
			.filter(Boolean)
			.slice(0, 2)
			.map((p) => p[0])
			.join("")
			.toUpperCase();
	}

	createApp({
		setup() {
			const boot = ref({ user: {}, can_manage: false, categories: [] });
			const week = ref({ days: [], slots: [], sessions: [], stats: {}, trainers: [] });
			const weekStart = ref("");
			const rangeDays = ref(1);
			const loading = ref(true);
			const error = ref("");
			const view = ref("dashboard");
			const filters = ref({
				instructor: "",
				student_group: "",
				room: "",
				status: "",
				search: "",
				search_by: "candidate",
			});
			const modalOpen = ref(false);
			const detailOpen = ref(false);
			const detail = ref(null);
			const detailStudents = ref([]);
			const detailPeople = ref([]);
			const weekStudents = ref({ groups: [], student_total: 0 });
			const saving = ref(false);
			const form = ref(emptyForm());
			const suggestions = ref({ StudentGroup: [], Instructor: [], Room: [], Customer: [], Course: [] });
			const candidateOpen = ref(false);
			const candidateSaving = ref(false);
			const candidateForm = ref(emptyCandidate());
			const csvInput = ref(null);
			const datePicker = ref({ open: false, field: "", year: 2026, month: 0 });
			const detailSearch = ref({ q: "", by: "candidate" });
			const rescheduleOpen = ref(false);
			const rescheduleSaving = ref(false);
			const reschedule = ref({ date: "", period: "morning" });

			function capacityText(row) {
				const invited = row?.invited || row?.booked || row?.student_count || 0;
				const came = row?.came || 0;
				const max = row?.max_strength || 0;
				if (max) return `${came} came · ${invited} invited · ${max} max`;
				return `${came} came · ${invited} invited`;
			}

			function capacityClass(row) {
				if (!row?.max_strength) return "";
				if (row.overbooked) return "full";
				if ((row.remaining || 0) === 0) return "full";
				if ((row.remaining || 0) <= Math.ceil(row.max_strength * 0.2)) return "low";
				return "ok";
			}

			function funnel(row) {
				const invited = Number(row?.invited || row?.booked || row?.student_count || 0);
				const came = Number(row?.came || 0);
				const max = Number(row?.max_strength || 0);
				const scale = max || invited || 1;
				const cameW = Math.min(100, (came / scale) * 100);
				const invitedOnly = Math.max(invited - came, 0);
				const invitedW = Math.min(100 - cameW, (invitedOnly / scale) * 100);
				return {
					max,
					invited,
					came,
					remaining: max ? Math.max(max - invited, 0) : null,
					cameW,
					invitedW,
					emptyW: Math.max(0, 100 - cameW - invitedW),
					marked: !!row?.attendance_marked,
				};
			}

			function attendanceLabel(status) {
				const value = (status || "").toLowerCase();
				if (value === "present") return "Came";
				if (value === "absent") return "No show";
				return "Invited";
			}

			function emptyCandidate() {
				return {
					name: "",
					candidate_name: "",
					names: [""],
					po_number: "",
					customer: "",
					customer_name: "",
					lunch: "No",
					date: "",
					student_group: "",
					course: "",
					course_schedule: "",
					create_student: false,
				};
			}

			function emptyForm() {
				return {
					name: "",
					date: "",
					period: "morning",
					from_time: "08:00",
					to_time: "12:00",
					student_group: "",
					student_group_name: "",
					customer_company: "",
					instructor: "",
					instructor_name: "",
					room: "",
					room_name: "",
					course: "",
					course_name: "",
					max_strength: 0,
					booked: 0,
					invited: 0,
					came: 0,
					attendance_marked: false,
					remaining: null,
				};
			}

			const visibleSessions = computed(() => {
				const instructor = filters.value.instructor;
				const group = filters.value.student_group;
				const room = filters.value.room;
				const status = filters.value.status;
				const q = (filters.value.search || "").trim().toLowerCase();
				return (week.value.sessions || []).filter((s) => {
					if (instructor && s.instructor !== instructor) return false;
					if (group && s.student_group !== group) return false;
					if (room && s.room !== room) return false;
					if (status && s.status !== status) return false;
					if (q) {
						const by = filters.value.search_by || "candidate";
						let blob = "";
						if (by === "candidate") {
							blob = [s.people_names, s.student_group_name].join(" ");
						} else if (by === "customer") {
							blob = [s.customer_company, s.customer].join(" ");
						} else if (by === "course") {
							blob = [s.course, s.course_name, s.student_group_name].join(" ");
						} else {
							blob = [
								s.people_names,
								s.instructor_name,
								s.course,
								s.student_group,
								s.student_group_name,
								s.customer_company,
								s.room_name,
							].join(" ");
						}
						if (!blob.toLowerCase().includes(q)) return false;
					}
					return true;
				});
			});

			const sessionsByCell = computed(() => {
				const map = {};
				visibleSessions.value.forEach((s) => {
					const key = `${s.date}|${s.period || "morning"}`;
					map[key] = map[key] || [];
					map[key].push(s);
				});
				return map;
			});

			function matchesSearch(values) {
				const q = (filters.value.search || "").trim().toLowerCase();
				if (!q) return true;
				return values.join(" ").toLowerCase().includes(q);
			}

			const filteredTrainers = computed(() =>
				(week.value.trainers || []).filter((t) =>
					matchesSearch([t.instructor_name, t.name])
				)
			);

			const filteredGroups = computed(() =>
				(week.value.groups || []).filter((g) =>
					matchesSearch([g.student_group, g.student_group_name, g.course, g.customer_company, g.instructor_name, g.room_name])
				)
			);

			const filteredRooms = computed(() =>
				(week.value.rooms || []).filter((r) =>
					matchesSearch([r.name, r.room_name, r.room_number])
				)
			);

			const detailSearchPlaceholder = computed(() => {
				const by = detailSearch.value.by || "candidate";
				if (by === "customer") return "Search by customer name";
				if (by === "po") return "Search by PO number";
				if (by === "course") return "Search by course name";
				return "Search by candidate name";
			});

			const filteredDetailPeople = computed(() => {
				const people = (detailPeople.value && detailPeople.value.length)
					? detailPeople.value
					: (detailStudents.value || []);
				const q = (detailSearch.value.q || "").trim().toLowerCase();
				if (!q) return people;
				const by = detailSearch.value.by || "candidate";
				const course = (detail.value && detail.value.course) || "";
				return people.filter((st) => {
					let blob = "";
					if (by === "customer") {
						blob = [st.company, st.customer_name].join(" ");
					} else if (by === "po") {
						blob = st.po_number || "";
					} else if (by === "course") {
						blob = [course, st.start_date, st.end_date].join(" ");
					} else {
						blob = [st.candidate_name, st.student_name, st.student].join(" ");
					}
					return blob.toLowerCase().includes(q);
				});
			});

			async function loadBoot() {
				boot.value = await call("get_boot");
				weekStart.value = boot.value.today || boot.value.week_start;
			}

			async function loadWeek() {
				loading.value = true;
				error.value = "";
				try {
					week.value = await call("get_week", {
						week_start: weekStart.value,
						days: rangeDays.value,
					});
					weekStart.value = week.value.week_start;
					if (view.value === "students") {
						await loadStudentsView();
					}
				} catch (e) {
					error.value = e.message;
				} finally {
					loading.value = false;
				}
			}

			function shiftWeek(dir) {
				const step = rangeDays.value <= 1 ? 1 : 7;
				const d = new Date(weekStart.value + "T00:00:00");
				d.setDate(d.getDate() + dir * step);
				weekStart.value = ymd(d);
				loadWeek();
			}

			function setRange(days) {
				if (days === rangeDays.value) return;
				if (days === 1) {
					const todayStr = boot.value.today || ymd(new Date());
					const inView = (week.value.days || []).some((d) => d.date === todayStr);
					weekStart.value = inView ? todayStr : (week.value.days?.[0]?.date || weekStart.value);
				}
				rangeDays.value = days;
				loadWeek();
			}

			function sessionsAt(day, slot) {
				return sessionsByCell.value[`${day.date}|${slot.key || slot.label?.toLowerCase() || "morning"}`] || [];
			}

			function openCreate(day, slot) {
				if (!boot.value.can_manage) return;
				form.value = {
					...emptyForm(),
					date: day?.date || weekStart.value,
					period: slot?.key || "morning",
					from_time: slot?.from_time || "08:00",
					to_time: slot?.to_time || "12:00",
				};
				modalOpen.value = true;
			}

			async function openDetail(session) {
				detailOpen.value = true;
				detail.value = session;
				detailStudents.value = [];
				detailPeople.value = [];
				detailSearch.value = { q: "", by: "candidate" };
				rescheduleOpen.value = false;
				datePicker.value.open = false;
				try {
					const data = await call("get_session_detail", { name: session.name });
					detail.value = data.session;
					detailStudents.value = data.students || [];
					detailPeople.value = data.people || data.students || [];
				} catch (e) {
					error.value = e.message;
				}
			}

			function openReschedule() {
				if (!detail.value) return;
				reschedule.value = {
					date: detail.value.date,
					period: detail.value.period || "morning",
				};
				error.value = "";
				datePicker.value.open = false;
				rescheduleOpen.value = true;
			}

			async function saveReschedule() {
				if (!detail.value?.name) return;
				if (!reschedule.value.date) {
					error.value = "New date is required.";
					return;
				}
				rescheduleSaving.value = true;
				error.value = "";
				try {
					const data = await call("reschedule_session", {
						name: detail.value.name,
						date: reschedule.value.date,
						period: reschedule.value.period || "morning",
					});
					rescheduleOpen.value = false;
					weekStart.value = data.date;
					await loadWeek();
					await openDetail({ name: data.name });
					if (view.value === "students") await loadStudentsView();
				} catch (e) {
					error.value = e.message;
				} finally {
					rescheduleSaving.value = false;
				}
			}
			function openEdit(session) {
				const src = session || detail.value || {};
				form.value = {
					name: src.name,
					date: src.date,
					period: src.period || "morning",
					from_time: src.time_start,
					to_time: src.time_end,
					student_group: src.student_group,
					student_group_name: src.student_group_name,
					customer_company: src.customer_company,
					instructor: src.instructor,
					instructor_name: src.instructor_name,
					room: src.room,
					room_name: src.room_name,
					course: src.course,
					course_name: src.course_name || src.course,
					max_strength: src.max_strength || 0,
					booked: src.booked || src.student_count || 0,
					invited: src.invited || src.booked || src.student_count || 0,
					came: src.came || 0,
					attendance_marked: !!src.attendance_marked,
					remaining: src.remaining,
				};
				detailOpen.value = false;
				modalOpen.value = true;
			}

			async function loadStudentsView() {
				try {
					weekStudents.value = await call("get_week_students", {
						week_start: weekStart.value,
						days: rangeDays.value,
						instructor: filters.value.instructor || null,
						student_group: filters.value.student_group || null,
						search: filters.value.search || null,
						search_by: filters.value.search_by || null,
					});
				} catch (e) {
					error.value = e.message;
				}
			}

			async function searchDoctype(doctype, txt, key) {
				const rows = await call("search_links", {
					doctype,
					txt,
					student_group: candidateForm.value.student_group || form.value.student_group || null,
				});
				suggestions.value[key] = (rows || []).map((row) => ({
					value: row[0],
					label: row[1] || row[0],
				}));
			}

			async function pickGroup(item) {
				form.value.student_group = item.value;
				form.value.student_group_name = item.label;
				suggestions.value.StudentGroup = [];
				const defaults = await call("get_student_group_defaults", {
					student_group: item.value,
					date: form.value.date || null,
				});
				form.value.course = defaults.course || "";
				form.value.course_name = defaults.course_name || defaults.course || "";
				form.value.customer_company = defaults.customer_company || "";
				form.value.room = defaults.room || form.value.room;
				form.value.room_name = defaults.room_name || form.value.room_name;
				form.value.max_strength = defaults.max_strength || 0;
				form.value.booked = defaults.booked || 0;
				form.value.invited = defaults.invited || defaults.booked || 0;
				form.value.came = defaults.came || 0;
				form.value.attendance_marked = !!defaults.attendance_marked;
				form.value.remaining = defaults.remaining;
				if (defaults.instructor) {
					form.value.instructor = defaults.instructor;
					form.value.instructor_name = defaults.instructor_name;
				}
			}

			function pickInstructor(item) {
				form.value.instructor = item.value;
				form.value.instructor_name = item.label;
				suggestions.value.Instructor = [];
			}

			function pickRoom(item) {
				form.value.room = item.value;
				form.value.room_name = item.label;
				suggestions.value.Room = [];
			}

			function pickCourse(item) {
				form.value.course = item.value;
				form.value.course_name = item.label;
				suggestions.value.Course = [];
			}

			function pickCustomer(item) {
				candidateForm.value.customer = item.value;
				candidateForm.value.customer_name = item.label;
				suggestions.value.Customer = [];
			}

			function formatDateLabel(iso) {
				if (!iso) return "";
				const d = new Date(String(iso).slice(0, 10) + "T00:00:00");
				if (Number.isNaN(d.getTime())) return iso;
				return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
			}

			function calendarCells() {
				const year = datePicker.value.year;
				const month = datePicker.value.month;
				const startDow = new Date(year, month, 1).getDay();
				const daysInMonth = new Date(year, month + 1, 0).getDate();
				const cells = [];
				for (let i = 0; i < startDow; i++) cells.push(null);
				for (let d = 1; d <= daysInMonth; d++) cells.push(d);
				return cells;
			}

			function calendarMonthLabel() {
				return new Date(datePicker.value.year, datePicker.value.month, 1).toLocaleDateString(undefined, {
					month: "long",
					year: "numeric",
				});
			}

			function openCalendar(field, current) {
				const raw = String(current || "").slice(0, 10);
				const d = raw ? new Date(raw + "T00:00:00") : new Date();
				const valid = !Number.isNaN(d.getTime()) ? d : new Date();
				datePicker.value = {
					open: datePicker.value.field === field ? !datePicker.value.open : true,
					field,
					year: valid.getFullYear(),
					month: valid.getMonth(),
				};
			}

			function shiftCalendar(delta) {
				let year = datePicker.value.year;
				let month = datePicker.value.month + delta;
				if (month < 0) {
					month = 11;
					year -= 1;
				} else if (month > 11) {
					month = 0;
					year += 1;
				}
				datePicker.value.year = year;
				datePicker.value.month = month;
			}

			function pickCalendarDay(day) {
				if (!day) return;
				const value = `${datePicker.value.year}-${String(datePicker.value.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
				if (datePicker.value.field === "candidate") candidateForm.value.date = value;
				else if (datePicker.value.field === "reschedule") reschedule.value.date = value;
				else form.value.date = value;
				datePicker.value.open = false;
			}

			function isSelectedDay(day) {
				if (!day) return false;
				let current = form.value.date;
				if (datePicker.value.field === "candidate") current = candidateForm.value.date;
				else if (datePicker.value.field === "reschedule") current = reschedule.value.date;
				const value = `${datePicker.value.year}-${String(datePicker.value.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
				return String(current || "").slice(0, 10) === value;
			}

			function onCandidateOverlayClick() {
				if (datePicker.value.open) {
					datePicker.value.open = false;
					return;
				}
				candidateOpen.value = false;
			}

			function openAddCandidate() {
				if (!detail.value) return;
				const people = detailPeople.value || detailStudents.value || [];
				const last = [...people].reverse().find((p) => p.po_number || p.customer || p.customer_name) || {};
				candidateForm.value = {
					...emptyCandidate(),
					names: [""],
					date: detail.value.date,
					student_group: detail.value.student_group,
					course: detail.value.course,
					course_schedule: detail.value.name,
					customer: last.customer || detail.value.customer || "",
					customer_name: last.customer_name || last.company || detail.value.customer_company || "",
					po_number: last.po_number || "",
					lunch: last.lunch || "No",
					create_student: false,
				};
				error.value = "";
				datePicker.value.open = false;
				candidateOpen.value = true;
			}

			function openEditCandidate(person) {
				if (!person?.candidate) return;
				candidateForm.value = {
					...emptyCandidate(),
					name: person.candidate,
					names: [person.candidate_name || ""],
					date: person.start_date || detail.value?.date || "",
					student_group: person.student_group || detail.value?.student_group || "",
					course: detail.value?.course || "",
					course_schedule: detail.value?.name || "",
					customer: person.customer || "",
					customer_name: person.company || person.customer_name || "",
					po_number: person.po_number || "",
					lunch: person.lunch === "Yes" ? "Yes" : "No",
					create_student: false,
				};
				error.value = "";
				datePicker.value.open = false;
				candidateOpen.value = true;
			}

			function addCandidateName() {
				candidateForm.value.names = [...(candidateForm.value.names || [""]), ""];
			}

			function removeCandidateName(idx) {
				const names = [...(candidateForm.value.names || [""])];
				if (names.length <= 1) {
					names[0] = "";
					candidateForm.value.names = names;
					return;
				}
				names.splice(idx, 1);
				candidateForm.value.names = names;
			}

			function candidateNamesToSave() {
				const names = candidateForm.value.names || [];
				const extra = candidateForm.value.candidate_name || "";
				return [...names, extra]
					.map((n) => String(n || "").trim())
					.filter((n, i, all) => n && all.findIndex((x) => x.toLowerCase() === n.toLowerCase()) === i);
			}

			async function saveCandidate() {
				const names = candidateNamesToSave();
				if (!names.length) {
					error.value = "Candidate name is required.";
					return;
				}
				if (!candidateForm.value.date) {
					error.value = "Date is required.";
					return;
				}
				candidateSaving.value = true;
				error.value = "";
				try {
					const payload = {
						name: candidateForm.value.name || "",
						candidate_names: names,
						po_number: candidateForm.value.po_number,
						customer: candidateForm.value.customer,
						customer_name: candidateForm.value.customer_name,
						lunch: candidateForm.value.lunch || "No",
						date: candidateForm.value.date,
						student_group: candidateForm.value.student_group,
						course: candidateForm.value.course,
						course_schedule: candidateForm.value.course_schedule,
						create_student: !!candidateForm.value.create_student,
					};
					if (candidateForm.value.name) {
						await call("update_candidate", { data: payload });
					} else {
						await call("add_candidate", { data: payload });
					}
					candidateOpen.value = false;
					if (detail.value?.name) await openDetail(detail.value);
					await loadWeek();
					if (view.value === "students") await loadStudentsView();
				} catch (e) {
					error.value = e.message;
				} finally {
					candidateSaving.value = false;
				}
			}

			async function deleteCandidate(person) {
				if (!boot.value.can_manage || !person?.candidate) return;
				const label = person.candidate_name || "this candidate";
				if (!confirm(`Delete ${label}?`)) return;
				saving.value = true;
				error.value = "";
				try {
					await call("delete_candidate", { name: person.candidate });
					if (detail.value?.name) await openDetail(detail.value);
					await loadWeek();
					if (view.value === "students") await loadStudentsView();
				} catch (e) {
					error.value = e.message;
				} finally {
					saving.value = false;
				}
			}

			function downloadCandidateCsvTemplate() {
				const csv = "Candidate Name,PO Number,Customer,Lunch\nJohn Smith,PO-123,Acme LLC,Yes\n";
				const blob = new Blob([csv], { type: "text/csv" });
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = "candidates-template.csv";
				a.click();
				URL.revokeObjectURL(url);
			}

			function exportSessionCandidatesCsv() {
				const rows = [
					["Candidate Name", "PO Number", "Customer", "Lunch", "Date", "Status"],
					...(filteredDetailPeople.value || []).map((p) => [
						p.candidate_name || p.student_name || "",
						p.po_number || "",
						p.company || p.customer_name || "",
						p.lunch || "No",
						p.start_date || "",
						p.can_create_student ? "Invited" : (p.attendance || "Student"),
					]),
				];
				const csv = rows.map((r) => r.map((v) => `"${String(v || "").replace(/"/g, '""')}"`).join(",")).join("\n");
				const blob = new Blob([csv], { type: "text/csv" });
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = `candidates-${(detail.value && detail.value.date) || "session"}.csv`;
				a.click();
				URL.revokeObjectURL(url);
			}

			function pickCandidateCsv() {
				csvInput.value && csvInput.value.click();
			}

			async function importCandidateCsv(event) {
				const file = event.target.files && event.target.files[0];
				event.target.value = "";
				if (!file || !detail.value?.name) return;
				candidateSaving.value = true;
				error.value = "";
				try {
					const csv_content = await file.text();
					const data = await call("import_candidates_csv", {
						data: {
							csv_content,
							date: detail.value.date,
							student_group: detail.value.student_group,
							course: detail.value.course,
							course_schedule: detail.value.name,
						},
					});
					if (detail.value?.name) await openDetail(detail.value);
					await loadWeek();
					if (view.value === "students") await loadStudentsView();
				} catch (e) {
					error.value = e.message;
				} finally {
					candidateSaving.value = false;
				}
			}

			async function createStudent(person) {
				if (!person?.candidate) return;
				saving.value = true;
				error.value = "";
				try {
					await call("create_student_from_candidate", { name: person.candidate });
					if (detail.value?.name) await openDetail(detail.value);
					await loadWeek();
					if (view.value === "students") await loadStudentsView();
				} catch (e) {
					error.value = e.message;
				} finally {
					saving.value = false;
				}
			}

			async function savePo(person, value) {
				if (!boot.value.can_manage || !person) return;
				const next = (value || "").trim();
				if ((person.po_number || "") === next) return;
				const previous = person.po_number || "";
				person.po_number = next;
				error.value = "";
				try {
					const data = await call("update_po_number", {
						candidate: person.candidate || "",
						student: person.student || "",
						student_group: person.student_group || detail.value?.student_group || "",
						po_number: next,
					});
					person.po_number = data.po_number || next;
				} catch (e) {
					person.po_number = previous;
					error.value = e.message;
				}
			}

			function searchPlaceholder() {
				const by = filters.value.search_by;
				if (by === "customer") return "Search by customer name";
				if (by === "course") return "Search by course name";
				return "Search by candidate name";
			}

			async function save() {
				if (!form.value.date) {
					error.value = "Date is required.";
					return;
				}
				if (!form.value.instructor) {
					error.value = "Instructor is required.";
					return;
				}
				saving.value = true;
				error.value = "";
				try {
					await call("save_session", { data: form.value });
					modalOpen.value = false;
					await loadWeek();
				} catch (e) {
					error.value = e.message;
				} finally {
					saving.value = false;
				}
			}

			async function removeSession() {
				if (!form.value.name) return;
				if (!confirm("Delete this session?")) return;
				await call("delete_session", { name: form.value.name });
				modalOpen.value = false;
				await loadWeek();
			}

			async function saveCapacity() {
				if (!detail.value?.student_group) return;
				saving.value = true;
				error.value = "";
				try {
					const data = await call("save_max_strength", {
						student_group: detail.value.student_group,
						max_strength: detail.value.max_strength || 0,
					});
					detail.value = { ...detail.value, ...data };
					await loadWeek();
				} catch (e) {
					error.value = e.message;
				} finally {
					saving.value = false;
				}
			}

			function exportCsv() {
				const rows = [
					["Date", "Schedule", "Student Group", "Customer/Company", "Instructor", "Room", "Course", "Booked", "Max Strength", "Remaining", "Status"],
					...visibleSessions.value.map((s) => [
						s.date,
						s.period_label || s.period,
						s.student_group_name,
						s.customer_company,
						s.instructor_name,
						s.room_name,
						s.course_name || s.course,
						s.booked || s.student_count,
						s.max_strength,
						s.remaining,
						s.status,
					]),
				];
				const csv = rows.map((r) => r.map((v) => `"${String(v || "").replace(/"/g, '""')}"`).join(",")).join("\n");
				const blob = new Blob([csv], { type: "text/csv" });
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = `training-schedule-${weekStart.value}.csv`;
				a.click();
				URL.revokeObjectURL(url);
			}

			function selectTrainer(trainer) {
				filters.value.instructor = trainer.name;
				filters.value.student_group = "";
				filters.value.room = "";
				view.value = "dashboard";
			}

			function selectGroup(group) {
				filters.value.student_group = group.student_group;
				filters.value.instructor = "";
				filters.value.room = "";
				view.value = "dashboard";
			}

			function selectRoom(room) {
				filters.value.room = room.name;
				filters.value.instructor = "";
				filters.value.student_group = "";
				view.value = "dashboard";
			}

			function clearTrainer() {
				filters.value.instructor = "";
			}

			function clearGroup() {
				filters.value.student_group = "";
			}

			function clearRoom() {
				filters.value.room = "";
			}

			const selectedTrainer = computed(() => {
				const id = filters.value.instructor;
				if (!id) return null;
				return (week.value.trainers || []).find((t) => t.name === id) || { name: id, instructor_name: id };
			});

			const selectedGroup = computed(() => {
				const id = filters.value.student_group;
				if (!id) return null;
				return (week.value.groups || []).find((g) => g.student_group === id) || { student_group: id, student_group_name: id };
			});

			const selectedRoom = computed(() => {
				const id = filters.value.room;
				if (!id) return null;
				return (week.value.rooms || []).find((r) => r.name === id) || { name: id, room_name: id };
			});

			const miniDays = computed(() => {
				if (!weekStart.value) return [];
				const start = new Date(weekStart.value + "T00:00:00");
				const monthStart = new Date(start.getFullYear(), start.getMonth(), 1);
				const firstDow = monthStart.getDay();
				const daysInMonth = new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate();
				const cells = [];
				for (let i = 0; i < firstDow; i++) cells.push("");
				for (let d = 1; d <= daysInMonth; d++) cells.push(d);
				return cells;
			});

			watch(view, (next) => {
				if (next === "students") {
					loadStudentsView();
				}
			});

			watch(
				() => [filters.value.search, filters.value.search_by, view.value],
				() => {
					if (view.value === "students") loadStudentsView();
				}
			);

			watch(
				() => [form.value.date, form.value.student_group],
				async () => {
					if (!modalOpen.value || !form.value.student_group || !form.value.date) return;
					try {
						const defaults = await call("get_student_group_defaults", {
							student_group: form.value.student_group,
							date: form.value.date,
						});
						form.value.invited = defaults.invited || defaults.booked || 0;
						form.value.booked = defaults.booked || 0;
						form.value.came = defaults.came || 0;
						form.value.attendance_marked = !!defaults.attendance_marked;
						form.value.remaining = defaults.remaining;
					} catch (e) {
						error.value = e.message;
					}
				}
			);

			onMounted(async () => {
				try {
					await loadBoot();
					await loadWeek();
				} catch (e) {
					if (String(e.message).toLowerCase().includes("login")) {
						window.location.href = "/login?redirect-to=/training-schedule";
						return;
					}
					error.value = e.message;
					loading.value = false;
				}
			});

			return {
				boot,
				week,
				weekStart,
				rangeDays,
				setRange,
				loading,
				error,
				view,
				filters,
				modalOpen,
				detailOpen,
				detail,
				detailStudents,
				detailPeople,
				weekStudents,
				saving,
				form,
				suggestions,
				candidateOpen,
				candidateSaving,
				candidateForm,
				csvInput,
				datePicker,
				detailSearch,
				rescheduleOpen,
				rescheduleSaving,
				reschedule,
				detailSearchPlaceholder,
				filteredDetailPeople,
				formatDateLabel,
				calendarCells,
				calendarMonthLabel,
				openCalendar,
				shiftCalendar,
				pickCalendarDay,
				isSelectedDay,
				onCandidateOverlayClick,
				formatWeek,
				initials,
				shiftWeek,
				loadWeek,
				sessionsAt,
				openCreate,
				openDetail,
				openEdit,
				openReschedule,
				saveReschedule,
				openAddCandidate,
				openEditCandidate,
				addCandidateName,
				removeCandidateName,
				candidateNamesToSave,
				saveCandidate,
				deleteCandidate,
				downloadCandidateCsvTemplate,
				exportSessionCandidatesCsv,
				pickCandidateCsv,
				importCandidateCsv,
				createStudent,
				savePo,
				searchDoctype,
				pickGroup,
				pickInstructor,
				pickRoom,
				pickCourse,
				pickCustomer,
				searchPlaceholder,
				save,
				saveCapacity,
				removeSession,
				exportCsv,
				miniDays,
				selectTrainer,
				selectGroup,
				selectRoom,
				clearTrainer,
				clearGroup,
				clearRoom,
				selectedTrainer,
				selectedGroup,
				selectedRoom,
				visibleSessions,
				filteredTrainers,
				filteredGroups,
				filteredRooms,
				loadStudentsView,
				capacityText,
				capacityClass,
				funnel,
				attendanceLabel,
			};
		},
		template: `
		<div class="ts-app">
			<aside class="ts-sidebar">
				<div class="ts-brand">TRAINING SCHEDULE</div>
				<nav class="ts-nav">
					<button :class="{active: view==='dashboard'}" @click="view='dashboard'">▦ Dashboard</button>
					<button :class="{active: view==='trainers'}" @click="view='trainers'">👤 Trainers</button>
					<button :class="{active: view==='students'}" @click="view='students'">🎓 Students</button>
					<button :class="{active: view==='groups'}" @click="view='groups'">📁 Student Groups</button>
					<button :class="{active: view==='schedules'}" @click="view='schedules'">📅 Course Schedule</button>
					<button :class="{active: view==='rooms'}" @click="view='rooms'">🚪 Rooms</button>
					<a href="/app/query-report">📊 Reports</a>
					<a href="/app">⚙️ Settings</a>
				</nav>
				<div class="ts-side-card">
					<div class="ts-stat-line"><span>Total Trainers</span><b>{{ week.stats.trainers || 0 }}</b></div>
					<div class="ts-stat-line" style="margin-top:8px"><span>Students this week</span><b>{{ week.stats.students || 0 }}</b></div>
				</div>
				<div class="ts-side-card">
					<h4>{{ week.week_start ? new Date(week.week_start+'T00:00:00').toLocaleString(undefined,{month:'long', year:'numeric'}) : '' }}</h4>
					<div class="ts-mini-cal">
						<span class="dow" v-for="d in ['S','M','T','W','T','F','S']" :key="d">{{ d }}</span>
						<span v-for="(d,i) in miniDays" :key="i"
							:class="{today: d && week.days && week.days.some(x => x.is_today && Number(x.date.slice(-2))===d), inWeek: d && week.days && week.days.some(x => Number(x.date.slice(-2))===d)}">
							{{ d }}
						</span>
					</div>
				</div>
			</aside>

			<main class="ts-main">
				<header class="ts-top">
					<div>
						<h1>Training Schedule</h1>
						<p v-if="selectedTrainer">
							Showing sessions for <b>{{ selectedTrainer.instructor_name }}</b>
							· {{ selectedTrainer.week_sessions || 0 }} sessions / {{ selectedTrainer.week_hours || 0 }} hrs this week
							· {{ selectedTrainer.year_sessions || 0 }} sessions / {{ selectedTrainer.year_hours || 0 }} hrs this year
							<button class="ts-btn" style="margin-left:8px;padding:4px 8px" @click="clearTrainer">Show all</button>
						</p>
						<p v-else-if="selectedGroup">
							Student group <b>{{ selectedGroup.student_group_name || selectedGroup.student_group }}</b>
							<button class="ts-btn" style="margin-left:8px;padding:4px 8px" @click="clearGroup">Show all</button>
						</p>
						<p v-else-if="selectedRoom">
							Room <b>{{ selectedRoom.room_name || selectedRoom.name }}</b>
							<button class="ts-btn" style="margin-left:8px;padding:4px 8px" @click="clearRoom">Show all</button>
						</p>
						<p v-else-if="view==='students'">Student details for this week's course schedules</p>
						<p v-else-if="view==='trainers'">Sessions and training hours by instructor</p>
						<p v-else-if="view==='groups'">Student groups scheduled this week</p>
						<p v-else-if="view==='schedules'">Course schedules this week. Times may be planning times, not classroom clock time.</p>
						<p v-else-if="view==='rooms'">Rooms used for this week's training</p>
						<p v-else>Planner for Morning, Afternoon and Evening sessions</p>
					</div>
					<div class="ts-top-right">
						<div class="ts-search-wrap">
							<select class="ts-select" v-model="filters.search_by">
								<option value="candidate">Candidate name</option>
								<option value="customer">Customer name</option>
								<option value="course">Course name</option>
							</select>
							<input class="ts-search" v-model="filters.search" :placeholder="searchPlaceholder()">
						</div>
						<button class="ts-bell" title="This week">🔔<b v-if="week.stats.in_progress">{{ week.stats.in_progress }}</b></button>
						<div class="ts-user">
							<div class="ts-avatar">
								<img v-if="boot.user.image" :src="boot.user.image">
								<template v-else>{{ boot.user.initials || 'U' }}</template>
							</div>
							<div>
								<strong>{{ boot.user.full_name || 'User' }}</strong>
								<small>{{ boot.user.role }}</small>
							</div>
						</div>
					</div>
				</header>

				<section class="ts-filters">
					<div class="ts-week-nav">
						<button @click="shiftWeek(-1)">‹</button>
						<div class="ts-week-label">{{ formatWeek(week.week_start, week.week_end) }}</div>
						<button @click="shiftWeek(1)">›</button>
						<div class="ts-range-toggle">
							<button :class="{active: rangeDays===1}" @click="setRange(1)">Day</button>
							<button :class="{active: rangeDays===7}" @click="setRange(7)">Week</button>
						</div>
					</div>
					<div class="ts-filter-actions">
						<select class="ts-select" v-model="filters.instructor">
							<option value="">All Trainers</option>
							<option v-for="t in week.trainers" :key="t.name" :value="t.name">{{ t.instructor_name }}</option>
						</select>
						<select class="ts-select" v-model="filters.status">
							<option value="">All Status</option>
							<option value="completed">Completed</option>
							<option value="in_progress">In Progress</option>
							<option value="upcoming">Upcoming</option>
						</select>
						<button v-if="boot.can_manage" class="ts-btn primary" @click="openCreate((week.days || [])[0], (week.slots || [])[0])">+ Add Session</button>
						<button class="ts-btn" @click="exportCsv">⤓ Export</button>
					</div>
				</section>

				<section class="ts-stats">
					<div class="ts-stat"><div class="ts-ico purple">▦</div><div><b>{{ week.stats.total || 0 }}</b><span>Total Sessions</span></div></div>
					<div class="ts-stat"><div class="ts-ico green">✓</div><div><b>{{ week.stats.completed || 0 }}</b><span>Completed</span></div></div>
					<div class="ts-stat"><div class="ts-ico orange">◷</div><div><b>{{ week.stats.in_progress || 0 }}</b><span>In Progress</span></div></div>
					<div class="ts-stat"><div class="ts-ico purple">📅</div><div><b>{{ week.stats.upcoming || 0 }}</b><span>Upcoming</span></div></div>
					<div class="ts-stat"><div class="ts-ico blue">⌂</div><div><b>{{ week.stats.rooms_used || 0 }} / {{ week.stats.rooms_total || 0 }}</b><span>Rooms Used</span></div></div>
					<div class="ts-stat"><div class="ts-ico green">☰</div><div><b>{{ week.stats.came || 0 }} / {{ week.stats.invited || week.stats.students || 0 }}</b><span>Came / Invited</span></div></div>
				</section>

				<p v-if="error && !modalOpen" class="ts-error" style="padding:0 24px">{{ error }}</p>
				<p v-if="loading" style="padding:0 24px;color:#6b7280">Loading schedule…</p>

				<section class="ts-grid-wrap" v-show="view==='dashboard'">
					<div class="ts-grid" :style="{'--ts-days': (week.days || []).length || 1}" :class="{oneDay: (week.days || []).length === 1}">
						<div class="ts-grid-head">
							<div class="ts-head">Schedule</div>
							<div class="ts-head" v-for="day in week.days" :key="day.date" :class="{today: day.is_today}">
								{{ day.label }}
								<b>{{ day.day_num }}</b>
							</div>
						</div>
						<div class="ts-grid-row" v-for="slot in week.slots" :key="slot.key || slot.label">
							<div class="ts-time">{{ slot.label }}</div>
							<div class="ts-cell" v-for="day in week.days" :key="day.date + (slot.key || slot.label)" @dblclick="openCreate(day, slot)">
								<template v-if="sessionsAt(day, slot).length">
									<div class="ts-card" v-for="s in sessionsAt(day, slot)" :key="s.name" :class="s.tone" @click="openDetail(s)">
										<div class="ts-card-top">
											<div class="ts-card-avatar">{{ initials(s.instructor_name) }}</div>
											<div>
												<strong>{{ s.course_name || s.course || s.customer_company || s.instructor_name || 'Session' }}</strong>
												<em>{{ s.instructor_name }}</em>
											</div>
										</div>
										<div class="ts-funnel ts-funnel-sm">
											<div class="ts-funnel-bar">
												<span class="came" :style="{width: funnel(s).cameW + '%'}"></span>
												<span class="invited" :style="{width: funnel(s).invitedW + '%'}"></span>
											</div>
											<div class="meta">{{ s.room_name || 'Room' }} · {{ capacityText(s) }}</div>
										</div>
									</div>
								</template>
								<div v-else class="empty">—</div>
							</div>
						</div>
					</div>
				</section>

				<section class="ts-grid-wrap" v-show="view==='trainers'">
					<div class="ts-grid ts-list-panel">
						<p class="ts-student-help">{{ week.stats.trainers_with_sessions || 0 }} trainers have sessions this week · {{ week.stats.hours || 0 }} training hours</p>
						<div v-if="!filteredTrainers.length" class="ts-empty-students">No trainers match this search.</div>
						<div v-for="t in filteredTrainers" :key="t.name" class="ts-trainer-row ts-list-card"
							:class="{active: filters.instructor===t.name}" @click="selectTrainer(t)">
							<div class="ts-avatar">{{ initials(t.instructor_name) }}</div>
							<div class="ts-list-main">
								<b>{{ t.instructor_name }}</b>
								<div class="ts-muted">{{ t.week_groups || 0 }} groups · {{ t.week_students || 0 }} students this week</div>
							</div>
							<div class="ts-metrics">
								<div><b>{{ t.week_sessions || 0 }}</b><span>sessions</span></div>
								<div><b>{{ t.week_hours || 0 }}</b><span>hrs week</span></div>
								<div><b>{{ t.year_sessions || 0 }}</b><span>sessions year</span></div>
								<div><b>{{ t.year_hours || 0 }}</b><span>hrs year</span></div>
							</div>
						</div>
					</div>
				</section>

				<section class="ts-grid-wrap" v-show="view==='students'">
					<div class="ts-grid ts-student-panel">
						<div class="ts-student-toolbar">
							<p class="ts-student-help">Students linked to Course Schedule via Student Group for this week.</p>
							<strong>{{ weekStudents.student_total || 0 }} students · {{ (weekStudents.groups || []).length }} groups</strong>
						</div>
						<div v-if="!(weekStudents.groups || []).length" class="ts-empty-students">No student groups in this week.</div>
						<div class="ts-group-block" v-for="g in weekStudents.groups" :key="g.student_group">
							<div class="ts-group-head">
								<div>
									<b>{{ g.course || g.student_group_name }}</b>
									<div class="ts-muted">{{ g.customer_company }} · {{ g.instructor_name }} · {{ g.room_name }}</div>
									<div class="ts-muted">{{ g.student_group }}</div>
									<div class="ts-session-chips">
										<span v-for="sess in (g.sessions || [])" :key="sess.name" @click="openDetail(sess)">{{ sess.date }} · {{ sess.period_label || 'Morning' }}</span>
									</div>
								</div>
								<span :class="'ts-cap '+capacityClass(g)">{{ capacityText(g) }}</span>
							</div>
							<table class="ts-table">
								<thead>
									<tr><th>#</th><th>Candidate</th><th>PO Number</th><th>Customer</th><th>Course</th><th>Course dates</th></tr>
								</thead>
								<tbody>
									<tr v-for="(st, idx) in (g.people || g.students || [])" :key="st.student || st.candidate || idx">
										<td>{{ st.group_roll_number || (idx+1) }}</td>
										<td>
											<a v-if="st.student" :href="'/app/student/' + st.student">{{ st.candidate_name || st.student_name }}</a>
											<span v-else>{{ st.candidate_name || st.student_name }}</span>
										</td>
										<td>
											<input v-if="boot.can_manage" class="ts-po-input" :value="st.po_number"
												placeholder="PO number"
												@blur="savePo(st, $event.target.value)"
												@keydown.enter.prevent="$event.target.blur()">
											<span v-else>{{ st.po_number || '—' }}</span>
										</td>
										<td>{{ st.company || st.customer_name || '—' }}</td>
										<td>{{ st.course_name || g.course || '—' }}</td>
										<td>{{ st.start_date || '—' }} to {{ st.end_date || '—' }}</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				</section>

				<section class="ts-grid-wrap" v-show="view==='groups'">
					<div class="ts-grid ts-list-panel">
						<div class="ts-student-toolbar">
							<p class="ts-student-help">Student groups with a course schedule this week. Click a row to see it on the planner.</p>
							<strong>{{ filteredGroups.length }} groups</strong>
						</div>
						<div v-if="!filteredGroups.length" class="ts-empty-students">No student groups in this week.</div>
						<table class="ts-table" v-else>
							<thead>
								<tr>
									<th>Student Group</th>
									<th>Course</th>
									<th>Customer</th>
									<th>Instructor</th>
									<th>Room</th>
									<th>Came / Invited / Max</th>
									<th>Remaining</th>
									<th>Sessions</th>
									<th>Hours</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="g in filteredGroups" :key="g.student_group" class="ts-click-row" @click="selectGroup(g)">
									<td>
										<b>{{ g.student_group_name || g.student_group }}</b>
										<div class="ts-muted">{{ g.student_group }}</div>
									</td>
									<td>{{ g.course || '—' }}</td>
									<td>{{ g.customer_company || '—' }}</td>
									<td>{{ g.instructor_name || '—' }}</td>
									<td>{{ g.room_name || '—' }}</td>
									<td>
										<div class="ts-funnel ts-funnel-sm">
											<div class="ts-funnel-bar">
												<span class="came" :style="{width: funnel(g).cameW + '%'}"></span>
												<span class="invited" :style="{width: funnel(g).invitedW + '%'}"></span>
											</div>
										</div>
										<span :class="'ts-cap '+capacityClass(g)">{{ g.came || 0 }} / {{ g.invited || g.booked || g.student_count || 0 }} / {{ g.max_strength || '—' }}</span>
									</td>
									<td>{{ g.max_strength ? (g.remaining || 0) : '—' }}</td>
									<td>{{ g.week_sessions || 0 }}</td>
									<td>{{ g.week_hours || 0 }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section class="ts-grid-wrap" v-show="view==='schedules'">
					<div class="ts-grid ts-list-panel">
						<div class="ts-student-toolbar">
							<p class="ts-student-help">Course schedules in this view. Click a row for student details.</p>
							<strong>{{ visibleSessions.length }} sessions · {{ week.stats.hours || 0 }} hrs</strong>
						</div>
						<div v-if="!visibleSessions.length" class="ts-empty-students">No course schedules in this week.</div>
						<table class="ts-table" v-else>
							<thead>
								<tr>
									<th>Date</th>
									<th>Schedule</th>
									<th>Course</th>
									<th>Instructor</th>
									<th>Student Group</th>
									<th>Customer</th>
									<th>Room</th>
									<th>Came / Invited / Max</th>
									<th>Remaining</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="s in visibleSessions" :key="s.name" class="ts-click-row" @click="openDetail(s)">
									<td>{{ s.date }}</td>
									<td>{{ s.period_label || 'Morning' }}</td>
									<td>{{ s.course_name || s.course || '—' }}</td>
									<td>{{ s.instructor_name || '—' }}</td>
									<td>{{ s.student_group_name || s.student_group || '—' }}</td>
									<td>{{ s.customer_company || '—' }}</td>
									<td>{{ s.room_name || '—' }}</td>
									<td>
										<div class="ts-funnel ts-funnel-sm">
											<div class="ts-funnel-bar">
												<span class="came" :style="{width: funnel(s).cameW + '%'}"></span>
												<span class="invited" :style="{width: funnel(s).invitedW + '%'}"></span>
											</div>
										</div>
										{{ s.came || 0 }} / {{ s.invited || s.booked || 0 }} / {{ s.max_strength || '—' }}
									</td>
									<td>{{ s.max_strength ? (s.remaining || 0) : '—' }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section class="ts-grid-wrap" v-show="view==='rooms'">
					<div class="ts-grid ts-list-panel">
						<div class="ts-student-toolbar">
							<p class="ts-student-help">Rooms in the portal. Click a room to see its sessions this week.</p>
							<strong>{{ week.stats.rooms_used || 0 }} used / {{ (week.rooms || []).length }} rooms</strong>
						</div>
						<div v-if="!filteredRooms.length" class="ts-empty-students">No rooms found.</div>
						<div v-for="r in filteredRooms" :key="r.name" class="ts-trainer-row ts-list-card"
							:class="{active: filters.room===r.name}" @click="selectRoom(r)">
							<div class="ts-avatar">{{ (r.room_name || r.name || 'R').slice(0,2).toUpperCase() }}</div>
							<div class="ts-list-main">
								<b>{{ r.room_name || r.name }}</b>
								<div class="ts-muted">{{ r.seating_capacity || 0 }} seats · {{ r.week_groups || 0 }} groups</div>
							</div>
							<div class="ts-metrics">
								<div><b>{{ r.week_sessions || 0 }}</b><span>sessions</span></div>
								<div><b>{{ r.week_hours || 0 }}</b><span>hrs week</span></div>
							</div>
						</div>
					</div>
				</section>

				<footer class="ts-legend">
					<div>
						<span class="ts-legend-item" v-for="c in boot.categories" :key="c.key"><i class="ts-dot" :class="'ts-card '+c.tone" style="border:0;min-height:10px;padding:0;width:10px;height:10px;display:inline-block"></i>{{ c.label }}</span>
					</div>
					<div>
						<span class="ts-legend-item"><i class="ts-dot" style="background:#22c55e"></i>Completed</span>
						<span class="ts-legend-item"><i class="ts-dot" style="background:#f59e0b"></i>In Progress</span>
						<span class="ts-legend-item"><i class="ts-dot" style="background:#8b5cf6"></i>Upcoming</span>
					</div>
				</footer>
			</main>

			<div class="ts-overlay" v-if="detailOpen" @click.self="detailOpen=false">
				<div class="ts-modal ts-detail-modal">
					<div class="ts-detail-head">
						<div>
							<h3>{{ (detail && (detail.course_name || detail.course || detail.customer_company || detail.instructor_name)) || 'Session' }}</h3>
							<p class="ts-muted" v-if="detail">{{ detail.date }} · {{ detail.period_label || 'Morning' }}</p>
						</div>
						<div class="ts-toolbar-actions">
							<button v-if="boot.can_manage && detail" class="ts-btn" @click="openReschedule">Reschedule</button>
							<button class="ts-btn" @click="detailOpen=false">Close</button>
						</div>
					</div>
						<div class="ts-reschedule" v-if="rescheduleOpen && boot.can_manage">
						<div>
							<label>New date</label>
							<div class="ts-datefield" @click.stop>
								<input type="text" readonly :value="formatDateLabel(reschedule.date)" placeholder="Select date"
									@click="openCalendar('reschedule', reschedule.date)">
								<button type="button" class="ts-cal-btn" @click="openCalendar('reschedule', reschedule.date)">📅</button>
								<div class="ts-cal" v-if="datePicker.open && datePicker.field==='reschedule'">
									<div class="ts-cal-head">
										<button type="button" @click="shiftCalendar(-1)">‹</button>
										<strong>{{ calendarMonthLabel() }}</strong>
										<button type="button" @click="shiftCalendar(1)">›</button>
									</div>
									<div class="ts-cal-dows"><span v-for="d in ['Su','Mo','Tu','We','Th','Fr','Sa']" :key="d">{{ d }}</span></div>
									<div class="ts-cal-grid">
										<button type="button" v-for="(day, i) in calendarCells()" :key="i" :disabled="!day"
											:class="{selected: isSelectedDay(day)}" @click="pickCalendarDay(day)">{{ day || '' }}</button>
									</div>
								</div>
							</div>
						</div>
						<div>
							<label>Schedule</label>
							<select class="ts-select" v-model="reschedule.period">
								<option value="morning">Morning</option>
								<option value="afternoon">Afternoon</option>
								<option value="evening">Evening</option>
							</select>
						</div>
						<div class="ts-reschedule-actions">
							<button class="ts-btn" @click="rescheduleOpen=false">Cancel</button>
							<button class="ts-btn primary" :disabled="rescheduleSaving" @click="saveReschedule">{{ rescheduleSaving ? 'Moving…' : 'Move session' }}</button>
						</div>
						<p class="ts-muted" style="grid-column:1/-1;margin:0">Candidates on this session move with it.</p>
					</div>
					<p class="ts-error" v-if="error && detailOpen" style="margin:0 0 12px">{{ error }}</p>
					<div class="ts-detail-meta" v-if="detail">
						<div><span>Name of training</span><b>{{ detail.course_name || detail.course || '—' }}</b></div>
						<div><span>Instructor</span><b>{{ detail.instructor_name || '—' }}</b></div>
						<div><span>Customer</span><b>{{ detail.customer_company || '—' }}</b></div>
						<div><span>Room</span><b>{{ detail.room_name || '—' }}</b></div>
						<div><span>Student Group</span><b>{{ detail.student_group_name || detail.student_group || '—' }}</b></div>
					</div>
					<div class="ts-capacity-box" v-if="detail">
						<div>
							<label>Max strength</label>
							<input type="number" min="0" v-model.number="detail.max_strength" :disabled="!boot.can_manage">
							<small>Manual capacity. Invited comes from Student Group.</small>
						</div>
						<div>
							<span>Invited</span>
							<b>{{ detail.invited || detail.booked || detailStudents.length || 0 }}</b>
							<small>Added on the student group</small>
						</div>
						<div>
							<span>Came</span>
							<b class="ts-cap ok">{{ detail.came || 0 }}</b>
							<small>{{ detail.attendance_marked ? ((detail.no_show || 0) + ' no show') : 'Attendance not marked' }}</small>
						</div>
						<div>
							<span>Seats left</span>
							<b :class="'ts-cap '+capacityClass(detail)">{{ detail.max_strength ? (detail.remaining || 0) : 'No max' }}</b>
						</div>
						<button v-if="boot.can_manage" class="ts-btn primary" :disabled="saving" @click="saveCapacity">{{ saving ? 'Saving…' : 'Save capacity' }}</button>
					</div>
					<div class="ts-funnel" v-if="detail">
						<div class="ts-funnel-bar ts-funnel-lg">
							<span class="came" :style="{width: funnel(detail).cameW + '%'}"></span>
							<span class="invited" :style="{width: funnel(detail).invitedW + '%'}"></span>
						</div>
						<div class="ts-funnel-legend">
							<span><i class="ts-dot" style="background:#22c55e"></i>Came {{ detail.came || 0 }}</span>
							<span><i class="ts-dot" style="background:#f59e0b"></i>Invited {{ detail.invited || detail.booked || 0 }}</span>
							<span><i class="ts-dot" style="background:#e5e7eb"></i>Max {{ detail.max_strength || '—' }}</span>
						</div>
					</div>
					<div class="ts-detail-students">
						<input ref="csvInput" type="file" accept=".csv,text/csv" class="ts-file-hidden" @change="importCandidateCsv">
						<div class="ts-student-toolbar">
							<strong>{{ filteredDetailPeople.length }}{{ detailSearch.q ? ' of ' + (detailPeople || detailStudents || []).length : '' }} students</strong>
							<div class="ts-toolbar-actions" v-if="boot.can_manage && detail">
								<button class="ts-btn" @click="openAddCandidate">Add Candidate</button>
								<button class="ts-btn" @click="pickCandidateCsv">Import CSV</button>
								<button class="ts-btn" @click="downloadCandidateCsvTemplate">CSV template</button>
								<button class="ts-btn" @click="exportSessionCandidatesCsv">Export CSV</button>
								<button class="ts-btn primary" @click="openEdit(detail)">Edit Session</button>
							</div>
						</div>
						<div class="ts-detail-search">
							<select class="ts-select" v-model="detailSearch.by">
								<option value="candidate">Candidate name</option>
								<option value="customer">Customer name</option>
								<option value="po">PO number</option>
								<option value="course">Course name</option>
							</select>
							<input class="ts-search" v-model="detailSearch.q" :placeholder="detailSearchPlaceholder">
						</div>
						<div v-if="!(detailPeople || detailStudents || []).length" class="ts-empty-students">No candidates on this session yet.</div>
						<div v-else-if="!filteredDetailPeople.length" class="ts-empty-students">No candidates match this search.</div>
						<table class="ts-table" v-else>
							<thead>
								<tr><th>#</th><th>Candidate</th><th>PO Number</th><th>Customer</th><th>Lunch</th><th>Status</th><th>Course dates</th><th></th></tr>
							</thead>
							<tbody>
								<tr v-for="(st, idx) in filteredDetailPeople" :key="st.student || st.candidate || idx">
									<td>{{ st.group_roll_number || (idx+1) }}</td>
									<td>
										<a v-if="st.student" :href="'/app/student/' + st.student">{{ st.candidate_name || st.student_name }}</a>
										<span v-else>{{ st.candidate_name || st.student_name }}</span>
									</td>
									<td>
										<input v-if="boot.can_manage" class="ts-po-input" :value="st.po_number"
											placeholder="PO number"
											@blur="savePo(st, $event.target.value)"
											@keydown.enter.prevent="$event.target.blur()">
										<span v-else>{{ st.po_number || '—' }}</span>
									</td>
									<td>{{ st.company || st.customer_name || '—' }}</td>
									<td>{{ st.lunch || 'No' }}</td>
										<td>
										<span class="ts-att" :class="st.can_create_student ? 'candidate' : (st.attendance || 'invited').toLowerCase()">
											{{ st.can_create_student ? 'Invited' : attendanceLabel(st.attendance) }}
										</span>
									</td>
									<td>{{ st.start_date || '—' }} to {{ st.end_date || '—' }}</td>
									<td class="ts-row-actions">
										<button v-if="boot.can_manage && st.candidate" class="ts-btn" @click="openEditCandidate(st)">Edit</button>
										<button v-if="boot.can_manage && st.candidate" class="ts-btn" @click="deleteCandidate(st)">Delete</button>
										<button v-if="boot.can_manage && st.can_create_student" class="ts-btn primary" :disabled="saving" @click="createStudent(st)">
											{{ saving ? 'Creating…' : 'Create Student' }}
										</button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>

			<div class="ts-overlay" v-if="modalOpen" @click.self="modalOpen=false">
				<div class="ts-modal">
					<h3>{{ form.name ? 'Edit Session' : 'Add Session' }}</h3>
					<div class="ts-form">
						<div>
							<label>Date <span class="ts-req">*</span></label>
							<div class="ts-datefield" @click.stop>
								<input type="text" readonly :value="formatDateLabel(form.date)" placeholder="Select date"
									@click="openCalendar('session', form.date)">
								<button type="button" class="ts-cal-btn" @click="openCalendar('session', form.date)">📅</button>
								<div class="ts-cal" v-if="datePicker.open && datePicker.field==='session'">
									<div class="ts-cal-head">
										<button type="button" @click="shiftCalendar(-1)">‹</button>
										<strong>{{ calendarMonthLabel() }}</strong>
										<button type="button" @click="shiftCalendar(1)">›</button>
									</div>
									<div class="ts-cal-dows"><span v-for="d in ['Su','Mo','Tu','We','Th','Fr','Sa']" :key="d">{{ d }}</span></div>
									<div class="ts-cal-grid">
										<button type="button" v-for="(day, i) in calendarCells()" :key="i" :disabled="!day"
											:class="{selected: isSelectedDay(day)}" @click="pickCalendarDay(day)">{{ day || '' }}</button>
									</div>
								</div>
							</div>
						</div>
						<div class="full">
							<label>Schedule</label>
							<select class="ts-select" v-model="form.period">
								<option value="morning">Morning</option>
								<option value="afternoon">Afternoon</option>
								<option value="evening">Evening</option>
							</select>
						</div>
						<div class="full ts-suggest">
							<label>Name of training</label>
							<input :value="form.course_name || form.course" placeholder="Search training / course"
								@focus="searchDoctype('Course', form.course_name || form.course || '', 'Course')"
								@input="form.course_name=$event.target.value; form.course=''; searchDoctype('Course', $event.target.value, 'Course')">
							<ul v-if="suggestions.Course.length">
								<li v-for="item in suggestions.Course" :key="item.value" @click="pickCourse(item)">{{ item.label }}</li>
							</ul>
						</div>
						<div class="full ts-suggest">
							<label>Student Group <span class="ts-optional">(optional)</span></label>
							<input :value="form.student_group_name || form.student_group" placeholder="Add after candidates arrive"
								@input="searchDoctype('Student Group', $event.target.value, 'StudentGroup')">
							<ul v-if="suggestions.StudentGroup.length">
								<li v-for="item in suggestions.StudentGroup" :key="item.value" @click="pickGroup(item)">
									{{ item.value }} — {{ item.label }}
								</li>
							</ul>
						</div>
						<div class="full">
							<label>Customer / Company</label>
							<input class="ts-readonly" :value="form.customer_company" readonly placeholder="Filled from Student Group">
						</div>
						<div>
							<label>Max strength</label>
							<input type="number" min="0" v-model.number="form.max_strength" placeholder="e.g. 50">
						</div>
						<div class="full" v-if="form.student_group">
							<div class="ts-funnel">
								<div class="ts-funnel-bar ts-funnel-lg">
									<span class="came" :style="{width: funnel(form).cameW + '%'}"></span>
									<span class="invited" :style="{width: funnel(form).invitedW + '%'}"></span>
								</div>
								<div class="ts-funnel-legend">
									<span><i class="ts-dot" style="background:#22c55e"></i>Came {{ form.came || 0 }}</span>
									<span><i class="ts-dot" style="background:#f59e0b"></i>Invited {{ form.invited || form.booked || 0 }}</span>
									<span><i class="ts-dot" style="background:#e5e7eb"></i>Max {{ form.max_strength || 0 }}</span>
									<span>Seats left {{ form.max_strength ? Math.max((form.max_strength || 0) - (form.invited || form.booked || 0), 0) : '—' }}</span>
								</div>
							</div>
						</div>
						<div class="ts-suggest">
							<label>Instructor <span class="ts-req">*</span></label>
							<input :value="form.instructor_name || form.instructor" placeholder="Search instructor"
								@input="searchDoctype('Instructor', $event.target.value, 'Instructor')">
							<ul v-if="suggestions.Instructor.length">
								<li v-for="item in suggestions.Instructor" :key="item.value" @click="pickInstructor(item)">{{ item.label }}</li>
							</ul>
						</div>
						<div class="ts-suggest">
							<label>Room</label>
							<input :value="form.room_name || form.room" placeholder="Search room"
								@input="searchDoctype('Room', $event.target.value, 'Room')">
							<ul v-if="suggestions.Room.length">
								<li v-for="item in suggestions.Room" :key="item.value" @click="pickRoom(item)">{{ item.label }}</li>
							</ul>
						</div>
						<p class="ts-error" v-if="error && modalOpen">{{ error }}</p>
					</div>
					<div class="ts-modal-actions">
						<button class="ts-btn" v-if="form.name" @click="removeSession">Delete</button>
						<button class="ts-btn" @click="modalOpen=false">Cancel</button>
						<button class="ts-btn primary" :disabled="saving" @click="save">{{ saving ? 'Saving…' : 'Save Session' }}</button>
					</div>
				</div>
			</div>

			<div class="ts-overlay ts-overlay-top" v-if="candidateOpen" @click.self="onCandidateOverlayClick">
				<div class="ts-modal">
					<h3>{{ candidateForm.name ? 'Edit Candidate' : 'Add Candidate' }}</h3>
					<p class="ts-muted" style="margin:-6px 0 12px">{{ candidateForm.name ? 'Update this candidate. Lunch is Yes or No.' : 'Same company, PO and lunch for everyone. Add more names below, or import a CSV.' }}</p>
					<div class="ts-form">
						<div class="full ts-suggest">
							<label>Customer name</label>
							<input :value="candidateForm.customer_name || candidateForm.customer" placeholder="Search customer"
								@input="candidateForm.customer_name=$event.target.value; candidateForm.customer=''; searchDoctype('Customer', $event.target.value, 'Customer')">
							<ul v-if="suggestions.Customer.length">
								<li v-for="item in suggestions.Customer" :key="item.value" @click="pickCustomer(item)">{{ item.label }}</li>
							</ul>
						</div>
						<div>
							<label>PO Number</label>
							<input v-model="candidateForm.po_number" placeholder="Customer PO">
						</div>
						<div>
							<label>Lunch</label>
							<select class="ts-select" v-model="candidateForm.lunch">
								<option value="Yes">Yes</option>
								<option value="No">No</option>
							</select>
						</div>
						<div>
							<label>Date</label>
							<div class="ts-datefield" @click.stop>
								<input type="text" readonly :value="formatDateLabel(candidateForm.date)" placeholder="Select date"
									@click="openCalendar('candidate', candidateForm.date)">
								<button type="button" class="ts-cal-btn" @click="openCalendar('candidate', candidateForm.date)">📅</button>
								<div class="ts-cal" v-if="datePicker.open && datePicker.field==='candidate'">
									<div class="ts-cal-head">
										<button type="button" @click="shiftCalendar(-1)">‹</button>
										<strong>{{ calendarMonthLabel() }}</strong>
										<button type="button" @click="shiftCalendar(1)">›</button>
									</div>
									<div class="ts-cal-dows"><span v-for="d in ['Su','Mo','Tu','We','Th','Fr','Sa']" :key="d">{{ d }}</span></div>
									<div class="ts-cal-grid">
										<button type="button" v-for="(day, i) in calendarCells()" :key="i" :disabled="!day"
											:class="{selected: isSelectedDay(day)}" @click="pickCalendarDay(day)">{{ day || '' }}</button>
									</div>
								</div>
							</div>
						</div>
						<div class="full ts-name-list">
							<label>Candidate names</label>
							<div class="ts-name-row" v-for="(name, idx) in candidateForm.names" :key="idx">
								<input v-model="candidateForm.names[idx]" :placeholder="idx === 0 ? 'Full name' : 'Another candidate'" :autofocus="idx===0">
								<button type="button" class="ts-name-remove" v-if="candidateForm.names.length > 1" @click="removeCandidateName(idx)" title="Remove">×</button>
							</div>
							<button type="button" class="ts-btn ts-add-name" v-if="!candidateForm.name" @click="addCandidateName">+ Add another candidate (same company &amp; PO)</button>
						</div>
						<p class="ts-error" v-if="error && candidateOpen">{{ error }}</p>
					</div>
					<div class="ts-modal-actions">
						<button class="ts-btn" @click="candidateOpen=false">Cancel</button>
						<button class="ts-btn primary" :disabled="candidateSaving" @click="saveCandidate">{{ candidateSaving ? 'Saving…' : (candidateForm.name ? 'Save Candidate' : (candidateNamesToSave().length > 1 ? 'Add ' + candidateNamesToSave().length + ' Candidates' : 'Add Candidate')) }}</button>
					</div>
				</div>
			</div>
		</div>
		`,
	}).mount("#training-schedule-app");
})();
