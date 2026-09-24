(() => {
	const { createApp, ref, computed, reactive, onMounted } = Vue;
	const API = "numerouno.numerouno.api.supplier_portal";

	const PILL = {
		"Pending review": ["#fdf0cf", "#7a4f00"],
		Approved: ["#e1ebfb", "#1d4f91"],
		Paid: ["#dcf1e2", "#1e6b3a"],
		"Needs info": ["#fde4e1", "#9a2419"],
		Open: ["#e1ebfb", "#1d4f91"],
		Invoiced: ["#fdf0cf", "#7a4f00"],
		Closed: ["#e6e9ee", "#4a5a70"],
		Valid: ["#dcf1e2", "#1e6b3a"],
		"Expiring soon": ["#fdf0cf", "#7a4f00"],
		Overdue: ["#fde4e1", "#9a2419"],
		"Under review": ["#e1ebfb", "#1d4f91"],
		"In stock": ["#dcf1e2", "#1e6b3a"],
		"Below reorder": ["#fdf0cf", "#7a4f00"],
		"Out of stock": ["#fde4e1", "#9a2419"],
	};

	function csrf() {
		return document.querySelector('meta[name="csrf-token"]')?.content || "";
	}

	async function call(method, args = {}) {
		const res = await fetch(`/api/method/${API}.${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
				"X-Frappe-CSRF-Token": csrf(),
			},
			credentials: "same-origin",
			body: JSON.stringify(args),
		});
		const data = await res.json();
		if (!res.ok || data.exc) {
			let message = "Request failed";
			try {
				if (data._server_messages) {
					const msgs = JSON.parse(data._server_messages);
					message = JSON.parse(msgs[0]).message || message;
				}
			} catch (e) {
				message = data.message || message;
			}
			throw new Error(message);
		}
		return data.message;
	}

	const fmtDate = (s) => {
		if (!s) return "—";
		const d = new Date(s + "T00:00:00");
		return d.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
	};

	const money = (n, c = "AED") =>
		new Intl.NumberFormat("en-AE", { style: "currency", currency: c || "AED" }).format(n || 0);

	const todayISO = () => {
		const d = new Date();
		d.setHours(0, 0, 0, 0);
		return d.toISOString().slice(0, 10);
	};

	const daysAgoISO = (days) => {
		const d = new Date();
		d.setHours(0, 0, 0, 0);
		d.setDate(d.getDate() - days);
		return d.toISOString().slice(0, 10);
	};

	const EMPTY_FORM = () => ({
		invoiceNumber: "",
		po: "",
		invoiceDate: "",
		dueDate: "",
		amount: "",
		currency: "AED",
		dnNumber: "",
		dnSigned: "",
		dnSignedDate: "",
		terms: "Net 30",
		note: "",
		certify: false,
	});

	createApp({
		setup() {
			const view = ref("submit");
			const step = ref(1);
			const maxStep = ref(1);
			const f = reactive(EMPTY_FORM());
			const file = ref(null);
			const fileInput = ref(null);
			const dnFile = ref(null);
			const dnFileInput = ref(null);
			const errors = reactive({});
			const drag = ref(false);
			const dnDrag = ref(false);
			const invoiceDateMin = daysAgoISO(7);
			const invoiceDateMax = todayISO();
			const subs = ref([]);
			const openPOs = ref([]);
			const orders = ref([]);
			const portal = ref({
				name: "NUMEROUNO",
				tagline: "SUPPLIER PORTAL",
				site_name: "numerouno",
				url: "/supplier-invoice-portal",
			});
			const vendor = ref({
				display_name: "ACME Manufacturing",
				contact_name: "Jessica Chen",
				vendor_id: "V-004812",
				ap_email: "ap@buyerco.com",
			});
			const requirePO = ref(true);
			const done = ref(false);
			const lastRef = ref("");
			const query = ref("");
			const filter = ref("All");
			const detail = ref(null);
			const submitting = ref(false);
			const demoMode = ref(true);
			const inventory = ref([]);
			const complianceDocs = ref([]);
			const threads = ref([]);
			const threadId = ref(1);
			const messageDraft = ref("");
			const helpArticles = ref([]);
			const profile = reactive({
				email: "",
				phone: "",
				address: "",
				payment_method: "Bank transfer",
				bank_account: "",
				notify_email: true,
				notify_status: true,
			});
			const profileSaved = ref(false);
			const docInput = ref(null);
			const docUploadTarget = ref(null);

			const topNav = computed(() => {
				const items = [
					{ id: "dashboard", label: "Dashboard" },
					{ id: "orders", label: "Orders" },
					{ id: "inventory", label: "Inventory" },
					{ id: "submit", label: "Invoicing" },
					{ id: "compliance", label: "Compliance" },
					{ id: "messages", label: "Messages" },
				];
				return items.map((n) => ({
					...n,
					active:
						n.id === "submit"
							? ["submit", "history"].includes(view.value)
							: view.value === n.id || (n.id === "dashboard" && view.value === "home"),
				}));
			});

			const sideNav = computed(() =>
				[
					["home", "Home"],
					["submit", "Submit Invoice"],
					["history", "Past Submissions"],
					["help", "Help Center"],
					["profile", "My Profile"],
				].map(([id, label]) => ({
					id,
					label,
					active: id === "home" ? view.value === "dashboard" : view.value === id,
				}))
			);

			const unreadCount = computed(() => threads.value.filter((t) => t.unread).length);

			const openOrders = computed(() => orders.value.filter((o) => o.status === "Open"));

			const outstandingAmount = computed(() =>
				subs.value.filter((s) => s.status !== "Paid").reduce((a, s) => a + (s.amount || 0), 0)
			);

			const attentionDocs = computed(() =>
				complianceDocs.value.filter((d) => d.status === "Expiring soon" || d.status === "Overdue")
			);

			const kpis = computed(() => [
				{
					label: "Open purchase orders",
					value: String(openOrders.value.length),
					note: money(openOrders.value.reduce((a, o) => a + (o.value || 0), 0)) + " ready to invoice",
					noteColor: "#5a6b82",
					go: () => go("orders"),
				},
				{
					label: "Outstanding invoices",
					value: String(subs.value.filter((s) => s.status !== "Paid").length),
					note: money(outstandingAmount.value) + " awaiting payment",
					noteColor: "#5a6b82",
					go: () => go("history"),
				},
				{
					label: "Compliance issues",
					value: String(attentionDocs.value.length),
					note: attentionDocs.value.length ? "Payment holds possible" : "All documents current",
					noteColor: attentionDocs.value.length ? "#9a2419" : "#1e6b3a",
					go: () => go("compliance"),
				},
				{
					label: "Unread messages",
					value: String(unreadCount.value),
					note: "From NumeroUNO",
					noteColor: "#5a6b82",
					go: () => go("messages"),
				},
			]);

			const todos = computed(() => {
				const list = [];
				subs.value
					.filter((s) => s.status === "Needs info")
					.forEach((s) => {
						list.push({
							text: `${s.num}: AP needs more information`,
							dot: "#d64545",
							cta: "View",
							action: () => {
								go("history");
								openDetail({ ...s, ...pill(s.status), amountFmt: money(s.amount, s.currency) });
							},
						});
					});
				attentionDocs.value.forEach((d) => {
					list.push({
						text: `${d.name}: ${d.status.toLowerCase()}`,
						dot: d.status === "Overdue" ? "#d64545" : "#e0a100",
						cta: "Upload",
						action: () => go("compliance"),
					});
				});
				openOrders.value.forEach((o) => {
					list.push({
						text: `${o.id} is ready to invoice`,
						dot: "#1d4f91",
						cta: "Invoice",
						action: () => invoicePo(o.id, o.value),
					});
				});
				return list;
			});

			const inventoryRows = computed(() =>
				inventory.value.map((i) => {
					const st =
						i.qty === 0 ? "Out of stock" : i.qty < i.reorder ? "Below reorder" : "In stock";
					return {
						...i,
						qtyFmt: Number(i.qty).toLocaleString(),
						reorderFmt: Number(i.reorder).toLocaleString(),
						status: st,
						pillStyle: pillStyle(st),
					};
				})
			);

			const complianceRows = computed(() =>
				complianceDocs.value.map((d) => ({
					...d,
					pillStyle: pillStyle(d.status),
				}))
			);

			const activeThread = computed(() => {
				const t = threads.value.find((x) => x.id === threadId.value) || threads.value[0];
				if (!t) return null;
				return {
					...t,
					msgs: (t.msgs || []).map((m) => ({
						...m,
						class: m.me ? "me" : "them",
					})),
				};
			});

			const threadList = computed(() =>
				threads.value.map((t) => ({
					...t,
					active: t.id === (activeThread.value?.id || threadId.value),
					fw: t.unread ? 700 : 500,
				}))
			);

			const pill = (status) => {
				const [bg, fg] = PILL[status] || PILL["Pending review"];
				return { pillBg: bg, pillFg: fg };
			};

			const pillStyle = (status) => {
				const p = pill(status);
				return { background: p.pillBg, color: p.pillFg };
			};

			const rows = computed(() =>
				subs.value.map((s) => ({
					...s,
					...pill(s.status),
					amountFmt: money(s.amount, s.currency),
				}))
			);

			const filtered = computed(() => {
				const q = query.value.trim().toLowerCase();
				return rows.value.filter(
					(r) =>
						(filter.value === "All" || r.status === filter.value) &&
						(!q || r.num.toLowerCase().includes(q) || (r.po || "").toLowerCase().includes(q))
				);
			});

			const recent = computed(() => rows.value.slice(0, 3));

			const steps = computed(() =>
				["1. Invoice Details", "2. Delivery Note", "3. Review & Submit"].map((label, i) => {
					const n = i + 1;
					const active = n === step.value;
					const reach = n <= maxStep.value;
					return {
						label,
						active,
						reach,
						class: active ? "active" : reach ? "done" : "pending",
					};
				})
			);

			const review = computed(() => {
				const signedLabel =
					f.dnSigned === "yes"
						? "Yes — signed by Numero employee"
						: f.dnSigned === "no"
							? "No — not signed"
							: "—";
				return [
					{ k: "Invoice #", v: f.invoiceNumber || "—" },
					{ k: "PO", v: f.po || "—" },
					{ k: "Invoice date", v: fmtDate(f.invoiceDate) },
					{ k: "Due date", v: fmtDate(f.dueDate) },
					{ k: "Total", v: money(parseFloat(String(f.amount).replace(/[,$]/g, "")) || 0, "AED") },
					{ k: "Currency", v: "AED" },
					{ k: "Invoice document", v: file.value ? file.value.name : "—" },
					{ k: "Delivery note #", v: f.dnNumber || "—" },
					{ k: "DN signed by Numero", v: signedLabel },
					{ k: "DN signed date", v: fmtDate(f.dnSignedDate) },
					{ k: "Signed DN document", v: dnFile.value ? dnFile.value.name : "—" },
					{ k: "Terms", v: f.terms },
				];
			});

			const openDetail = (row) => {
				detail.value = {
					...row,
					timeline: [
						{ what: "Submitted by " + vendor.value.contact_name, when: row.date },
						{ what: "In AP review queue", when: "Est. 2–3 business days" },
					],
				};
			};

			const attachFile = (blob, target) => {
				if (!blob) return;
				const errKey = target === "dn" ? "dnFile" : "file";
				if (blob.size > 10 * 1024 * 1024) {
					errors[errKey] = "File exceeds 10 MB.";
					return;
				}
				const kb = blob.size / 1024;
				const meta = {
					name: blob.name,
					size: kb > 1024 ? (kb / 1024).toFixed(1) + " MB" : Math.max(1, Math.round(kb)) + " KB",
					blob,
				};
				if (target === "dn") {
					dnFile.value = meta;
					dnDrag.value = false;
				} else {
					file.value = meta;
					drag.value = false;
				}
				errors[errKey] = undefined;
			};

			const takeFile = (blob) => attachFile(blob, "invoice");
			const takeDnFile = (blob) => attachFile(blob, "dn");

			const validateInvoiceDate = () => {
				if (!f.invoiceDate) {
					errors.invoiceDate = "Required";
					return;
				}
				const min = daysAgoISO(7);
				const max = todayISO();
				if (f.invoiceDate > max) {
					errors.invoiceDate = "Future invoice dates are not allowed.";
				} else if (f.invoiceDate < min) {
					errors.invoiceDate = "Invoice date cannot be more than 7 days in the past.";
				}
			};

			const validate = (s) => {
				Object.keys(errors).forEach((k) => delete errors[k]);
				if (s === 1) {
					if (!file.value) errors.file = "Attach the invoice document.";
					if (!f.invoiceNumber.trim()) errors.invoiceNumber = "Required";
					else if (subs.value.some((x) => x.num.toLowerCase() === f.invoiceNumber.trim().toLowerCase()))
						errors.invoiceNumber = "This invoice number was already submitted.";
					if (requirePO.value && !f.po) errors.po = "Select the PO this invoice bills against.";
					validateInvoiceDate();
					if (!f.dueDate) errors.dueDate = "Required";
					else if (f.invoiceDate && f.dueDate < f.invoiceDate)
						errors.dueDate = "Due date must be after invoice date.";
					const a = parseFloat(String(f.amount).replace(/[,$]/g, ""));
					if (!(a > 0)) errors.amount = "Enter an amount greater than 0.";
					f.currency = "AED";
				}
				if (s === 2) {
					if (!f.dnNumber.trim()) errors.dnNumber = "Delivery note number is required.";
					if (!f.dnSigned) errors.dnSigned = "Confirm whether the DN is signed by a Numero employee.";
					else if (f.dnSigned === "no")
						errors.dnSigned =
							"Delivery notes must be signed by a Numero employee before invoice submission.";
					if (f.dnSigned === "yes") {
						if (!f.dnSignedDate) errors.dnSignedDate = "Enter the date the DN was signed.";
						else if (f.dnSignedDate > todayISO())
							errors.dnSignedDate = "Signed date cannot be in the future.";
						if (!dnFile.value) errors.dnFile = "Upload the signed delivery note document.";
					}
				}
				if (s === 3 && !f.certify) errors.certify = "Please confirm before submitting.";
				return Object.keys(errors).length === 0;
			};

			const next = async () => {
				if (!validate(step.value)) return;
				if (step.value < 3) {
					step.value += 1;
					maxStep.value = Math.max(maxStep.value, step.value);
					return;
				}
				submitting.value = true;
				try {
					const res = await call("submit_invoice", {
						payload: {
							invoice_number: f.invoiceNumber.trim(),
							po: f.po,
							invoice_date: f.invoiceDate,
							due_date: f.dueDate,
							amount: parseFloat(String(f.amount).replace(/[,$]/g, "")),
							currency: "AED",
							dn_number: f.dnNumber.trim(),
							dn_signed: f.dnSigned,
							dn_signed_date: f.dnSignedDate,
							dn_document_name: dnFile.value?.name || "",
							invoice_document_name: file.value?.name || "",
							terms: f.terms,
							note: f.note,
						},
					});
					const today = new Date().toLocaleDateString("en-US", {
						month: "short",
						day: "2-digit",
						year: "numeric",
					});
					subs.value.unshift({
						num: f.invoiceNumber.trim(),
						po: f.po || "—",
						date: today,
						due: fmtDate(f.dueDate),
						amount: parseFloat(String(f.amount).replace(/[,$]/g, "")),
						currency: "AED",
						status: "Pending review",
					});
					lastRef.value = res.reference || "NU-DEMO";
					done.value = true;
				} catch (e) {
					alert(e.message || "Submit failed");
				} finally {
					submitting.value = false;
				}
			};

			const resetForm = () => {
				Object.assign(f, EMPTY_FORM());
				file.value = null;
				dnFile.value = null;
				step.value = 1;
				maxStep.value = 1;
				done.value = false;
				view.value = "submit";
			};

			const go = (v) => {
				view.value = v;
				detail.value = null;
			};

			const invoicePo = (poId, amount) => {
				Object.assign(f, EMPTY_FORM());
				file.value = null;
				dnFile.value = null;
				step.value = 1;
				maxStep.value = 1;
				f.po = poId;
				if (amount) f.amount = String(amount);
				view.value = "submit";
				done.value = false;
			};

			const pickThread = (id) => {
				threadId.value = id;
				threads.value = threads.value.map((t) =>
					t.id === id ? { ...t, unread: false } : t
				);
			};

			const sendMessage = () => {
				const txt = messageDraft.value.trim();
				if (!txt || !activeThread.value) return;
				const tid = activeThread.value.id;
				threads.value = threads.value.map((t) =>
					t.id === tid
						? {
								...t,
								msgs: [...(t.msgs || []), { me: true, text: txt, meta: "You · just now" }],
							}
						: t
				);
				messageDraft.value = "";
			};

			const onMessageKeydown = (e) => {
				if (e.key === "Enter" && !e.shiftKey) {
					e.preventDefault();
					sendMessage();
				}
			};

			const triggerDocUpload = (docId) => {
				docUploadTarget.value = docId;
				docInput.value?.click();
			};

			const onDocFile = (e) => {
				const fileObj = e.target.files?.[0];
				e.target.value = "";
				if (!fileObj || !docUploadTarget.value) return;
				const id = docUploadTarget.value;
				complianceDocs.value = complianceDocs.value.map((d) =>
					d.id === id
						? {
								...d,
								status: "Under review",
								meta: `${fileObj.name} uploaded just now`,
							}
						: d
				);
				docUploadTarget.value = null;
			};

			const saveProfile = () => {
				profileSaved.value = true;
				setTimeout(() => {
					profileSaved.value = false;
				}, 2500);
			};

			onMounted(async () => {
				try {
					const boot = await call("get_bootstrap");
					if (boot.portal) portal.value = boot.portal;
					if (boot.vendor) vendor.value = boot.vendor;
					if (boot.open_pos) openPOs.value = boot.open_pos;
					if (boot.submissions) subs.value = boot.submissions;
					if (boot.orders) orders.value = boot.orders;
					if (boot.inventory) inventory.value = boot.inventory;
					if (boot.compliance_docs) complianceDocs.value = boot.compliance_docs;
					if (boot.message_threads) {
						threads.value = boot.message_threads;
						threadId.value = boot.message_threads[0]?.id || 1;
					}
					if (boot.help_articles) helpArticles.value = boot.help_articles;
					if (boot.profile) Object.assign(profile, boot.profile);
					requirePO.value = boot.require_po !== false;
					demoMode.value = !!boot.demo_mode;
					f.currency = "AED";
				} catch (e) {
					console.warn("Bootstrap failed, using client defaults", e);
				}
			});

			return {
				view,
				step,
				f,
				file,
				fileInput,
				dnFile,
				dnFileInput,
				errors,
				drag,
				dnDrag,
				invoiceDateMin,
				invoiceDateMax,
				done,
				lastRef,
				query,
				filter,
				detail,
				submitting,
				demoMode,
				portal,
				vendor,
				openPOs,
				orders,
				topNav,
				sideNav,
				steps,
				review,
				recent,
				filtered,
				requirePO,
				go,
				next,
				resetForm,
				openDetail,
				takeFile,
				takeDnFile,
				invoicePo,
				pillStyle,
				fmtDate,
				money,
				filters: ["All", "Pending review", "Approved", "Needs info", "Paid"],
				historyCount: computed(
					() =>
						`${subs.value.length} invoices · ${money(outstandingAmount.value)} outstanding`
				),
				inventory,
				inventoryRows,
				complianceRows,
				helpArticles,
				profile,
				profileSaved,
				saveProfile,
				kpis,
				todos,
				unreadCount,
				threadList,
				activeThread,
				messageDraft,
				pickThread,
				sendMessage,
				onMessageKeydown,
				docInput,
				triggerDocUpload,
				onDocFile,
			};
		},
		template: `
<div class="sip-shell">
  <header class="sip-header">
    <div class="sip-brand"><strong>{{ portal.name }}</strong><span>{{ portal.tagline }}</span></div>
    <nav class="sip-topnav">
      <button v-for="n in topNav" :key="n.id" type="button" :class="{ active: n.active }" @click="go(n.id === 'submit' ? 'submit' : n.id)">{{ n.label }}</button>
    </nav>
    <div class="sip-header-user">
      <button type="button" class="sip-bell" title="Messages" @click="go('messages')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path></svg>
        <span v-if="unreadCount" class="sip-bell-badge">{{ unreadCount }}</span>
      </button>
      <div>Welcome, <strong>{{ vendor.contact_name }}</strong><div class="muted">{{ vendor.display_name }}</div></div>
    </div>
  </header>
  <div class="sip-body">
    <aside class="sip-aside">
      <button v-for="s in sideNav" :key="s.id" type="button" :class="{ active: s.active }" @click="go(s.id === 'home' ? 'dashboard' : s.id)">{{ s.label }}</button>
      <div class="sip-aside-foot">Vendor ID <code>{{ vendor.vendor_id }}</code><br>AP contact: {{ vendor.ap_email }}</div>
    </aside>
    <main class="sip-main">
      <template v-if="view === 'submit'">
        <div v-if="!done">
          <h1 class="sip-title">Invoice Submission Portal</h1>
          <p class="sip-sub">Submit invoices against open purchase orders in AED. After submit, NumeroUNO AP reviews within 2–3 business days. <a href="/supplier-registration">New supplier? Register here</a>.</p>
          <div class="sip-steps" style="margin-top:18px">
            <button v-for="(st, i) in steps" :key="i" type="button" class="sip-step" :class="st.class" :disabled="!st.reach" @click="st.reach && (step = i + 1)">{{ st.label }}</button>
          </div>
          <section class="sip-card" style="margin-top:14px">
            <div v-show="step === 1" class="sip-grid-2">
              <div>
                <input ref="fileInput" type="file" accept=".pdf,.png,.jpg,.jpeg" style="display:none" @change="e => takeFile(e.target.files[0])" />
                <div v-if="!file" class="sip-upload" :class="{ drag }" @click="fileInput?.click()" @dragover.prevent="drag = true" @dragleave="drag = false" @drop.prevent="e => takeFile(e.dataTransfer.files[0])">
                  <div class="sip-upload-title">UPLOAD INVOICE</div>
                  <div class="sip-sub">Drag a file here or browse · PDF, PNG or JPG · max 10 MB</div>
                  <div v-if="errors.file" class="sip-err">{{ errors.file }}</div>
                </div>
                <div v-else class="sip-card" style="min-height:240px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px">
                  <div style="font-weight:600">{{ file.name }}</div>
                  <div class="sip-sub">{{ file.size }} · Uploaded</div>
                  <div style="display:flex;gap:8px">
                    <button type="button" class="sip-btn secondary sm" @click="fileInput?.click()">Replace</button>
                    <button type="button" class="sip-btn secondary sm" @click="file = null">Remove</button>
                  </div>
                </div>
              </div>
              <div style="display:flex;flex-direction:column;gap:14px">
                <div class="sip-field"><label>Invoice Number *</label><div><input v-model="f.invoiceNumber" placeholder="e.g. INV-2026-0418" /><div v-if="errors.invoiceNumber" class="sip-err">{{ errors.invoiceNumber }}</div></div></div>
                <div class="sip-field"><label>PO Number<span v-if="requirePO"> *</span></label><div><select v-model="f.po"><option value="">Select open PO</option><option v-for="p in openPOs" :key="p.id" :value="p.id">{{ p.label }}</option></select><div v-if="errors.po" class="sip-err">{{ errors.po }}</div></div></div>
                <div class="sip-field"><label>Invoice Date *</label><div><input v-model="f.invoiceDate" type="date" :min="invoiceDateMin" :max="invoiceDateMax" /><div class="sip-sub" style="margin-top:4px">Today or up to 7 days back · future dates blocked</div><div v-if="errors.invoiceDate" class="sip-err">{{ errors.invoiceDate }}</div></div></div>
                <div class="sip-field"><label>Due Date *</label><div><input v-model="f.dueDate" type="date" /><div v-if="errors.dueDate" class="sip-err">{{ errors.dueDate }}</div></div></div>
                <div class="sip-field"><label>Total Amount (AED) *</label><div style="display:flex;gap:8px;align-items:flex-start"><span class="sip-chip active" style="pointer-events:none;min-width:64px;justify-content:center">AED</span><input v-model="f.amount" class="mono" placeholder="0.00" style="flex:1" /><div v-if="errors.amount" class="sip-err">{{ errors.amount }}</div></div></div>
              </div>
            </div>
            <div v-show="step === 2" style="max-width:640px;display:flex;flex-direction:column;gap:18px">
              <p class="sip-sub" style="margin:0">Delivery notes must be signed by a Numero employee before the invoice is accepted for AP review.</p>
              <div class="sip-field" style="grid-template-columns:180px 1fr"><label>Delivery Note # *</label><div><input v-model="f.dnNumber" placeholder="e.g. DN-2026-0124" /><div v-if="errors.dnNumber" class="sip-err">{{ errors.dnNumber }}</div></div></div>
              <div>
                <div style="font-weight:600;margin-bottom:8px">Signed by Numero employee? *</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap">
                  <button type="button" class="sip-chip" :class="{ active: f.dnSigned === 'yes' }" @click="f.dnSigned = 'yes'">Yes — signed</button>
                  <button type="button" class="sip-chip" :class="{ active: f.dnSigned === 'no' }" @click="f.dnSigned = 'no'">Not signed</button>
                </div>
                <div v-if="errors.dnSigned" class="sip-err">{{ errors.dnSigned }}</div>
              </div>
              <div class="sip-field" style="grid-template-columns:180px 1fr"><label>Date signed *</label><div><input v-model="f.dnSignedDate" type="date" :max="invoiceDateMax" :disabled="f.dnSigned !== 'yes'" /><div v-if="errors.dnSignedDate" class="sip-err">{{ errors.dnSignedDate }}</div></div></div>
              <div>
                <input ref="dnFileInput" type="file" accept=".pdf,.png,.jpg,.jpeg" style="display:none" @change="e => takeDnFile(e.target.files[0])" />
                <div v-if="!dnFile" class="sip-upload" :class="{ drag: dnDrag }" @click="dnFileInput?.click()" @dragover.prevent="dnDrag = true" @dragleave="dnDrag = false" @drop.prevent="e => takeDnFile(e.dataTransfer.files[0])">
                  <div class="sip-upload-title">UPLOAD SIGNED DELIVERY NOTE</div>
                  <div class="sip-sub">Signed DN document · PDF, PNG or JPG · max 10 MB</div>
                  <div v-if="errors.dnFile" class="sip-err">{{ errors.dnFile }}</div>
                </div>
                <div v-else class="sip-card" style="min-height:140px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px">
                  <div style="font-weight:600">{{ dnFile.name }}</div>
                  <div class="sip-sub">{{ dnFile.size }} · Uploaded</div>
                  <div style="display:flex;gap:8px">
                    <button type="button" class="sip-btn secondary sm" @click="dnFileInput?.click()">Replace</button>
                    <button type="button" class="sip-btn secondary sm" @click="dnFile = null">Remove</button>
                  </div>
                </div>
              </div>
              <div class="sip-field" style="grid-template-columns:180px 1fr"><label>Payment Terms</label><select v-model="f.terms"><option>Net 30</option><option>Net 45</option><option>Net 60</option></select></div>
              <div class="sip-field" style="grid-template-columns:180px 1fr;align-items:start"><label>Note to AP</label><textarea v-model="f.note" rows="3" style="padding:9px 12px;border:1px solid #cfd6e0;border-radius:6px;width:100%"></textarea></div>
            </div>
            <div v-show="step === 3">
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:#e3e8ef;border:1px solid #e3e8ef;border-radius:6px;overflow:hidden">
                <div v-for="r in review" :key="r.k" style="background:#fff;padding:12px 14px"><div style="font-size:12px;color:#5a6b82;text-transform:uppercase">{{ r.k }}</div><div style="font-weight:600;margin-top:3px">{{ r.v }}</div></div>
              </div>
              <p class="sip-sub" style="margin-top:14px">After you submit, this invoice and signed delivery note go to <strong>NumeroUNO AP</strong> for review.</p>
              <label style="display:flex;gap:10px;margin-top:12px;font-size:14px;cursor:pointer"><input v-model="f.certify" type="checkbox" /> I certify this invoice is accurate, the delivery note is signed by a Numero employee, and it has not been submitted previously.</label>
              <div v-if="errors.certify" class="sip-err">{{ errors.certify }}</div>
            </div>
            <div class="sip-actions">
              <button v-if="step > 1" type="button" class="sip-btn secondary" @click="step--">Back</button>
              <span v-else></span>
              <button type="button" class="sip-btn" :disabled="submitting" @click="next">{{ step === 3 ? (submitting ? 'Submitting…' : 'Submit invoice') : 'Continue' }}</button>
            </div>
          </section>
        </div>
        <section v-else class="sip-card sip-success">
          <div class="sip-success-icon">✓</div>
          <h2>Invoice submitted to NumeroUNO</h2>
          <p class="sip-sub">Reference <strong class="mono">{{ lastRef }}</strong> is now with NumeroUNO AP for review (typically 2–3 business days).</p>
          <div style="display:flex;gap:10px;margin-top:10px">
            <button type="button" class="sip-btn" @click="resetForm">+ Submit new invoice</button>
            <button type="button" class="sip-btn secondary" @click="go('history')">View submissions</button>
          </div>
        </section>
        <section v-if="!done" class="sip-card flush">
          <div style="padding:14px 18px;border-bottom:1px solid #e3e8ef;font-weight:700">Recent submissions</div>
          <div class="sip-table-wrap">
            <table class="sip-table"><thead><tr><th>Invoice #</th><th>PO</th><th>Submitted</th><th>Status</th><th></th></tr></thead>
              <tbody><tr v-for="s in recent" :key="s.num"><td class="mono">{{ s.num }}</td><td>{{ s.po }}</td><td>{{ s.date }}</td><td><span class="sip-pill" :style="{ background: s.pillBg, color: s.pillFg }">{{ s.status }}</span></td><td><a href="#" @click.prevent="openDetail(s)">View details</a></td></tr></tbody>
            </table>
          </div>
        </section>
      </template>

      <template v-else-if="view === 'history'">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:16px">
          <div><h1 class="sip-title">Past Submissions</h1><p class="sip-sub">{{ historyCount }}</p></div>
          <button type="button" class="sip-btn" @click="go('submit')">+ Submit new invoice</button>
        </div>
        <div class="sip-filters">
          <input v-model="query" placeholder="Search invoice or PO #" />
          <button v-for="fl in filters" :key="fl" type="button" class="sip-chip" :class="{ active: filter === fl }" @click="filter = fl">{{ fl }}</button>
        </div>
        <section class="sip-card flush sip-table-wrap">
          <table class="sip-table" style="min-width:720px"><thead><tr><th>Invoice #</th><th>PO</th><th>Submitted</th><th>Due</th><th>Amount</th><th>Status</th><th></th></tr></thead>
            <tbody><tr v-for="s in filtered" :key="s.num"><td class="mono">{{ s.num }}</td><td>{{ s.po }}</td><td>{{ s.date }}</td><td>{{ s.due }}</td><td class="mono" style="text-align:right">{{ s.amountFmt }}</td><td><span class="sip-pill" :style="{ background: s.pillBg, color: s.pillFg }">{{ s.status }}</span></td><td><a href="#" @click.prevent="openDetail(s)">View details</a></td></tr></tbody>
          </table>
          <div v-if="!filtered.length" style="padding:28px;text-align:center;color:#5a6b82">No submissions match your filters.</div>
        </section>
      </template>

      <template v-else-if="view === 'dashboard' || view === 'home'">
        <h1 class="sip-title">Dashboard</h1>
        <p class="sip-sub">Account overview for {{ vendor.display_name }}</p>
        <div class="sip-kpis">
          <button v-for="k in kpis" :key="k.label" type="button" class="sip-kpi" @click="k.go()">
            <div class="sip-sub">{{ k.label }}</div>
            <div class="val">{{ k.value }}</div>
            <div class="sip-sub" :style="{ color: k.noteColor, marginTop: '4px' }">{{ k.note }}</div>
          </button>
        </div>
        <section class="sip-card flush">
          <div style="padding:14px 18px;border-bottom:1px solid #e3e8ef;font-weight:700">Needs your attention</div>
          <div v-if="!todos.length" style="padding:18px;color:#5a6b82;font-size:14px">You're all caught up.</div>
          <div v-for="(t, idx) in todos" :key="idx" class="sip-todo-row">
            <div style="display:flex;align-items:center;gap:12px;min-width:0">
              <span class="sip-todo-dot" :style="{ background: t.dot }"></span>
              <span style="font-size:14px">{{ t.text }}</span>
            </div>
            <button type="button" class="sip-btn secondary sm" @click="t.action()">{{ t.cta }}</button>
          </div>
        </section>
      </template>

      <template v-else-if="view === 'inventory'">
        <h1 class="sip-title">Inventory</h1>
        <p class="sip-sub">Your items stocked at NumeroUNO warehouses (consignment view)</p>
        <section class="sip-card flush sip-table-wrap">
          <table class="sip-table" style="min-width:680px">
            <thead><tr><th>SKU</th><th>Item</th><th>Location</th><th style="text-align:right">On hand</th><th style="text-align:right">Reorder at</th><th>Stock</th></tr></thead>
            <tbody>
              <tr v-for="i in inventoryRows" :key="i.sku">
                <td class="mono">{{ i.sku }}</td><td>{{ i.name }}</td><td style="color:#5a6b82">{{ i.loc }}</td>
                <td class="mono" style="text-align:right">{{ i.qtyFmt }}</td>
                <td class="mono" style="text-align:right;color:#5a6b82">{{ i.reorderFmt }}</td>
                <td><span class="sip-pill" :style="i.pillStyle">{{ i.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>

      <template v-else-if="view === 'orders'">
        <h1 class="sip-title">Purchase Orders</h1>
        <p class="sip-sub">POs issued to your company</p>
        <section class="sip-card flush sip-table-wrap">
          <table class="sip-table"><thead><tr><th>PO #</th><th>Description</th><th>Issued</th><th>Value</th><th>Status</th><th></th></tr></thead>
            <tbody><tr v-for="o in orders" :key="o.id"><td class="mono">{{ o.id }}</td><td>{{ o.desc }}</td><td>{{ o.issued }}</td><td class="mono">{{ money(o.value) }}</td><td><span class="sip-pill" :style="pillStyle(o.status)">{{ o.status }}</span></td><td><button v-if="o.status === 'Open'" type="button" class="sip-btn sm" @click="invoicePo(o.id, o.value)">Invoice this PO</button></td></tr></tbody>
          </table>
        </section>
      </template>

      <template v-else-if="view === 'compliance'">
        <h1 class="sip-title">Compliance</h1>
        <p class="sip-sub">Keep these documents current to stay eligible for payment</p>
        <input ref="docInput" type="file" accept=".pdf,.png,.jpg,.jpeg" style="display:none" @change="onDocFile" />
        <section class="sip-card flush">
          <div v-for="d in complianceRows" :key="d.id" style="display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px 18px;border-top:1px solid #e3e8ef;flex-wrap:wrap">
            <div style="min-width:0">
              <div style="font-size:14px;font-weight:600">{{ d.name }}</div>
              <div style="font-size:13px;color:#5a6b82;margin-top:2px">{{ d.meta }}</div>
            </div>
            <div style="display:flex;align-items:center;gap:12px">
              <span class="sip-pill" :style="d.pillStyle">{{ d.status }}</span>
              <button type="button" class="sip-btn secondary sm" @click="triggerDocUpload(d.id)">Upload new</button>
            </div>
          </div>
        </section>
      </template>

      <template v-else-if="view === 'messages'">
        <h1 class="sip-title">Messages</h1>
        <div class="sip-msg-layout">
          <div style="border-right:1px solid #e3e8ef;display:flex;flex-direction:column">
            <button v-for="th in threadList" :key="th.id" type="button" class="sip-msg-thread" :class="{ active: th.active }" @click="pickThread(th.id)">
              <div style="display:flex;justify-content:space-between;gap:8px">
                <span :style="{ fontWeight: th.fw }">{{ th.from }}</span>
                <span style="font-size:12px;color:#5a6b82">{{ th.when }}</span>
              </div>
              <div style="font-size:13px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ th.subject }}</div>
            </button>
          </div>
          <div v-if="activeThread" style="display:flex;flex-direction:column;min-width:0">
            <div style="padding:14px 20px;border-bottom:1px solid #e3e8ef">
              <div style="font-size:15px;font-weight:700">{{ activeThread.subject }}</div>
              <div style="font-size:13px;color:#5a6b82;margin-top:2px">{{ activeThread.from }}</div>
            </div>
            <div style="flex:1;padding:18px 20px;display:flex;flex-direction:column;gap:12px;overflow:auto;min-height:280px">
              <div v-for="(m, mi) in activeThread.msgs" :key="mi" class="sip-msg-bubble" :class="m.class">
                <div>{{ m.text }}</div>
                <div style="font-size:11px;margin-top:4px;opacity:.75">{{ m.meta }}</div>
              </div>
            </div>
            <div style="padding:12px 16px;border-top:1px solid #e3e8ef;display:flex;gap:8px">
              <input v-model="messageDraft" placeholder="Write a reply…" style="flex:1;min-width:0;height:38px;padding:0 12px;border:1px solid #cfd6e0;border-radius:6px" @keydown="onMessageKeydown" />
              <button type="button" class="sip-btn sm" @click="sendMessage">Send</button>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="view === 'help'">
        <h1 class="sip-title">Help Center</h1>
        <p class="sip-sub">Quick answers for suppliers using {{ portal.name }} ({{ portal.site_name }})</p>
        <section class="sip-card flush">
          <details v-for="(h, hi) in helpArticles" :key="hi" class="sip-help-item" :open="hi === 0">
            <summary>{{ h.title }}</summary>
            <p>{{ h.body }}</p>
          </details>
        </section>
        <section class="sip-card" style="margin-top:14px;font-size:14px;line-height:1.55">
          <strong>Still need help?</strong> Email <a :href="'mailto:' + vendor.ap_email">{{ vendor.ap_email }}</a> or open
          <a href="#" @click.prevent="go('messages')">Messages</a> to reach Accounts Payable.
        </section>
      </template>

      <template v-else-if="view === 'profile'">
        <h1 class="sip-title">My Profile</h1>
        <p class="sip-sub">Contact and payment preferences for {{ vendor.display_name }}</p>
        <section class="sip-card">
          <div class="sip-profile-grid">
            <div class="sip-field" style="grid-template-columns:140px 1fr"><label>Contact name</label><input :value="vendor.contact_name" disabled /></div>
            <div class="sip-field" style="grid-template-columns:140px 1fr"><label>Company</label><input :value="vendor.display_name" disabled /></div>
            <div class="sip-field" style="grid-template-columns:140px 1fr"><label>Email</label><input v-model="profile.email" type="email" /></div>
            <div class="sip-field" style="grid-template-columns:140px 1fr"><label>Phone</label><input v-model="profile.phone" /></div>
            <div class="sip-field" style="grid-template-columns:140px 1fr;align-items:start"><label>Remit address</label><textarea v-model="profile.address" rows="2" style="padding:9px 12px;border:1px solid #cfd6e0;border-radius:6px;width:100%"></textarea></div>
            <div class="sip-field" style="grid-template-columns:140px 1fr"><label>Payment method</label><select v-model="profile.payment_method"><option>Bank transfer</option><option>Cheque</option></select></div>
            <div class="sip-field" style="grid-template-columns:140px 1fr"><label>Bank on file</label><input v-model="profile.bank_account" /></div>
          </div>
          <label class="sip-check-row"><input v-model="profile.notify_email" type="checkbox" /> Email me when invoice status changes</label>
          <label class="sip-check-row"><input v-model="profile.notify_status" type="checkbox" /> Notify about compliance expirations</label>
          <div class="sip-actions" style="border-top:0;padding-top:8px;margin-top:12px">
            <span v-if="profileSaved" style="color:#1e6b3a;font-size:14px;font-weight:600">Profile saved</span>
            <span v-else></span>
            <button type="button" class="sip-btn" @click="saveProfile">Save profile</button>
          </div>
        </section>
      </template>
    </main>
  </div>

  <template v-if="detail">
    <div class="sip-drawer-backdrop" @click="detail = null"></div>
    <aside class="sip-drawer">
      <div class="sip-drawer-head">
        <div><div class="sip-sub" style="text-transform:uppercase;font-size:12px">Invoice</div><div class="mono" style="font-size:18px;font-weight:700">{{ detail.num }}</div></div>
        <button type="button" class="sip-btn secondary sm" @click="detail = null">×</button>
      </div>
      <div style="padding:20px">
        <span class="sip-pill" :style="{ background: detail.pillBg, color: detail.pillFg }">{{ detail.status }}</span>
        <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:14px">
          <div><div class="sip-sub">PO</div><strong>{{ detail.po }}</strong></div>
          <div><div class="sip-sub">Amount</div><strong>{{ detail.amountFmt }}</strong></div>
        </div>
      </div>
    </aside>
  </template>
</div>
		`,
	}).mount("#supplier-invoice-portal");
})();
