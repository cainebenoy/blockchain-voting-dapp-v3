import { supabase } from './db.js';

// --- ENROLLMENT SERVICE WITH PERSISTENCE (Supabase) ---

export const queueEnrollment = async (data) => {
    try {
        const { data: request, error } = await supabase
            .from('enrollment_requests')
            .insert([{
                ...data,
                status: 'PENDING',
                created_at: new Date().toISOString()
            }])
            .select()
            .single();

        if (error) throw error;
        return request;
    } catch (e) {
        console.error("Queue Enroll Error:", e);
        throw e;
    }
};

export const getEnrollmentStatus = async (id = null) => {
    try {
        let query = supabase.from('enrollment_requests').select('*');

        if (id) {
            query = query.eq('id', id);
        } else {
            query = query.eq('status', 'PENDING').order('created_at', { ascending: false }).limit(1);
        }

        const { data, error } = await query.maybeSingle();

        if (error) throw error;

        if (data) {
            if (data.status === 'PENDING') {
                const created = new Date(data.created_at).getTime();
                const now = Date.now();
                if (now - created > 600000) { // Increased to 10 minutes to fix TZ issues
                    console.log(`[ENROLL DEBUG] Enrollment ${data.id} TIMED OUT. Created: ${created}, Now: ${now}, Diff: ${now - created}`);
                    await supabase
                        .from('enrollment_requests')
                        .update({ status: 'FAILED', error_message: 'Timed out' })
                        .eq('id', data.id);
                    return { status: 'IDLE' };
                }
                console.log(`[ENROLL DEBUG] Found pending enrollment: ${data.id} for ${data.name}`);
                // Ensure the returned status reflects 'WAITING_FOR_KIOSK'. Spread data first
                // so we can override the `status` field reliably.
                return { ...data, status: 'WAITING_FOR_KIOSK' };
            }
            return data;
        }

        return { status: 'IDLE' };
    } catch (e) {
        console.error("Get Status Error:", e);
        return { status: 'ERROR', error: e.message };
    }
};

export const getPendingEnrollment = async () => {
    // Alias for getEnrollmentStatus but returns raw object or null
    const result = await getEnrollmentStatus();
    if (result.status === 'WAITING_FOR_KIOSK') return result;
    return null;
};

export const setEnrollmentStatus = async (id, status, errorMsg = null) => {
    try {
        const update = { status };
        if (errorMsg) update.error_message = errorMsg;

        const { error } = await supabase
            .from('enrollment_requests')
            .update(update)
            .eq('id', id);

        if (error) throw error;
    } catch (e) {
        console.error("Set Status Error:", e);
    }
};

