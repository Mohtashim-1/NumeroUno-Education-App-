(() => {
	const { createApp, ref, reactive, onMounted } = Vue;
	const API = "numerouno.numerouno.api.supplier_registration";

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

	const EMPTY = () => ({
		supplier_name: "",
		supplier_type: "Company",
		trade_license: "",
		tax_id: "",
		country: "United Arab Emirates",
		city: "",
		emirate: "Abu Dhabi",
		contact_person: "",
		email: "",
		mobile_no: "",
		phone: "",
		address_line1: "",
		address_line2: "",
		bank_name: "",
		iban: "",
		account_name: "",
		payment_terms: "Net 30",
		goods_services: "",
		remarks: "",
	});

	createApp({
		setup() {
			const f = reactive(EMPTY());
			const errors = reactive({});
			const submitting = ref(false);
			const done = ref(false);
			const refName = ref("");
			const emirates = ref([
				"Abu Dhabi",
				"Dubai",
				"Sharjah",
				"Ajman",
				"Umm Al Quwain",
				"Ras Al Khaimah",
				"Fujairah",
			]);
			const formError = ref("");

			const validate = () => {
				Object.keys(errors).forEach((k) => delete errors[k]);
				formError.value = "";
				const req = [
					["supplier_name", "Company name is required"],
					["contact_person", "Contact person is required"],
					["email", "Email is required"],
					["mobile_no", "Mobile is required"],
					["address_line1", "Address is required"],
					["city", "City is required"],
				];
				req.forEach(([k, msg]) => {
					if (!(f[k] || "").trim()) errors[k] = msg;
				});
				if (f.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim())) {
					errors.email = "Enter a valid email";
				}
				return Object.keys(errors).length === 0;
			};

			const submit = async () => {
				if (!validate()) return;
				submitting.value = true;
				formError.value = "";
				try {
					const res = await call("submit_supplier_registration", { payload: { ...f } });
					refName.value = res.name;
					done.value = true;
				} catch (e) {
					formError.value = e.message || "Submission failed";
				} finally {
					submitting.value = false;
				}
			};

			const reset = () => {
				Object.assign(f, EMPTY());
				done.value = false;
				refName.value = "";
				formError.value = "";
			};

			onMounted(async () => {
				try {
					const ctx = await call("get_registration_context");
					if (ctx?.emirates?.length) emirates.value = ctx.emirates;
				} catch (e) {
					/* defaults ok */
				}
			});

			return { f, errors, submitting, done, refName, emirates, formError, submit, reset };
		},
		template: `
<div class="sip-shell" style="min-height:100vh">
  <header class="sip-header">
    <div class="sip-brand"><strong>NUMEROUNO</strong><span>SUPPLIER REGISTRATION</span></div>
    <div class="sip-header-user">
      <a href="/supplier-invoice-portal" style="color:#fff;text-decoration:none;font-size:14px">Invoice Portal →</a>
    </div>
  </header>
  <div class="sr-wrap">
    <div class="sr-topbar">
      <div>
        <h1 class="sip-title" style="margin:0">Register as a Supplier</h1>
        <p class="sip-sub" style="margin:6px 0 0">Submit your company details. NumeroUNO AP will review and approve your account.</p>
      </div>
    </div>

    <section v-if="!done" class="sr-card">
      <div class="sr-grid">
        <div class="sr-section">Company</div>
        <div class="sr-field sr-full">
          <label>Supplier / Company Name <span class="req">*</span></label>
          <input v-model="f.supplier_name" placeholder="Legal company name" />
          <div v-if="errors.supplier_name" class="sr-err">{{ errors.supplier_name }}</div>
        </div>
        <div class="sr-field">
          <label>Supplier Type</label>
          <select v-model="f.supplier_type"><option>Company</option><option>Individual</option></select>
        </div>
        <div class="sr-field">
          <label>Trade License No.</label>
          <input v-model="f.trade_license" />
        </div>
        <div class="sr-field">
          <label>Tax / VAT Number</label>
          <input v-model="f.tax_id" />
        </div>
        <div class="sr-field">
          <label>Preferred Payment Terms</label>
          <select v-model="f.payment_terms"><option>Net 30</option><option>Net 45</option><option>Net 60</option><option>Immediate</option></select>
        </div>

        <div class="sr-section">Primary Contact</div>
        <div class="sr-field">
          <label>Contact Person <span class="req">*</span></label>
          <input v-model="f.contact_person" />
          <div v-if="errors.contact_person" class="sr-err">{{ errors.contact_person }}</div>
        </div>
        <div class="sr-field">
          <label>Email <span class="req">*</span></label>
          <input v-model="f.email" type="email" placeholder="ap@supplier.com" />
          <div v-if="errors.email" class="sr-err">{{ errors.email }}</div>
        </div>
        <div class="sr-field">
          <label>Mobile <span class="req">*</span></label>
          <input v-model="f.mobile_no" placeholder="+971 …" />
          <div v-if="errors.mobile_no" class="sr-err">{{ errors.mobile_no }}</div>
        </div>
        <div class="sr-field">
          <label>Phone</label>
          <input v-model="f.phone" />
        </div>

        <div class="sr-section">Address</div>
        <div class="sr-field sr-full">
          <label>Address Line 1 <span class="req">*</span></label>
          <input v-model="f.address_line1" />
          <div v-if="errors.address_line1" class="sr-err">{{ errors.address_line1 }}</div>
        </div>
        <div class="sr-field sr-full">
          <label>Address Line 2</label>
          <input v-model="f.address_line2" />
        </div>
        <div class="sr-field">
          <label>City <span class="req">*</span></label>
          <input v-model="f.city" />
          <div v-if="errors.city" class="sr-err">{{ errors.city }}</div>
        </div>
        <div class="sr-field">
          <label>Emirate</label>
          <select v-model="f.emirate"><option v-for="e in emirates" :key="e" :value="e">{{ e }}</option></select>
        </div>
        <div class="sr-field">
          <label>Country</label>
          <input v-model="f.country" readonly />
        </div>

        <div class="sr-section">Bank (AED)</div>
        <div class="sr-field">
          <label>Bank Name</label>
          <input v-model="f.bank_name" />
        </div>
        <div class="sr-field">
          <label>Account Name</label>
          <input v-model="f.account_name" />
        </div>
        <div class="sr-field sr-full">
          <label>IBAN</label>
          <input v-model="f.iban" class="mono" placeholder="AE…" />
        </div>

        <div class="sr-section">Other</div>
        <div class="sr-field sr-full">
          <label>Goods / Services Supplied</label>
          <textarea v-model="f.goods_services" rows="2"></textarea>
        </div>
        <div class="sr-field sr-full">
          <label>Remarks</label>
          <textarea v-model="f.remarks" rows="2"></textarea>
        </div>
      </div>

      <div v-if="formError" class="sr-err" style="margin-top:14px">{{ formError }}</div>
      <div class="sr-actions">
        <button type="button" class="sip-btn" :disabled="submitting" @click="submit">
          {{ submitting ? 'Submitting…' : 'Submit for approval' }}
        </button>
      </div>
    </section>

    <section v-else class="sr-card sr-success">
      <div class="sr-success-icon">✓</div>
      <h2 style="margin:0 0 8px">Registration submitted</h2>
      <p class="sip-sub">Reference <strong class="mono">{{ refName }}</strong> is with NumeroUNO for approval.</p>
      <p class="sip-sub">You will be able to use the Supplier Invoice Portal once your account is approved.</p>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:18px;flex-wrap:wrap">
        <button type="button" class="sip-btn secondary" @click="reset">Register another</button>
        <a class="sip-btn" href="/supplier-invoice-portal" style="text-decoration:none;display:inline-flex;align-items:center">Invoice Portal</a>
      </div>
    </section>
  </div>
</div>
`,
	}).mount("#supplier-registration");
})();
