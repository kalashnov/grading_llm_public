// ============================================================
// GRADESCOPE ANSWER GROUP BATCH CREATOR
// Course: ECON120B_SP26_A00 (ID: 1288622)
// Exams: Midterm 1 - VA, VB, VC, VD
// Skips: questions with no schema (1.c, 1.g, 1.h, 1.i)
//        and already-graded question 2.b (3.2)
// ============================================================

const courseId = 1288622;

function getCSRF() {
  return document.querySelector('meta[name="csrf-token"]').content;
}

async function setGroupingType(questionId) {
  const resp = await fetch(`/courses/${courseId}/questions/${questionId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-CSRF-Token': getCSRF(),
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify({ question: { assisted_grading_type: 'complex' } })
  });
  return resp.status;
}

async function createGroup(questionId, title) {
  const resp = await fetch(`/courses/${courseId}/questions/${questionId}/answer_groups`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-CSRF-Token': getCSRF(),
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify({ title: title, internal_title: null })
  });
  const data = await resp.json();
  return { status: resp.status, id: data.id, title: data.title };
}

async function deleteGroupFn(questionId, groupId) {
  const resp = await fetch(`/courses/${courseId}/questions/${questionId}/answer_groups/${groupId}`, {
    method: 'DELETE',
    headers: {
      'X-CSRF-Token': getCSRF(),
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'application/json'
    }
  });
  return resp.status;
}

async function getGroups(questionId) {
  const resp = await fetch(`/courses/${courseId}/questions/${questionId}/answer_groups`, {
    headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
  });
  const data = await resp.json();
  return data.groups || [];
}

async function getAssignmentQuestions(assignmentId) {
  const resp = await fetch(`/courses/${courseId}/assignments/${assignmentId}.json`, {
    headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
  });
  const data = await resp.json();
  const assignData = data.assignments[assignmentId];
  return Object.values(assignData.questions)
    .filter(q => q.type !== 'QuestionGroup' && q.total_count > 0)
    .map(q => ({ id: q.id, title: q.title, totalGraded: q.total_graded_count }));
}

// Schema: question title -> ordered list of 2^k group names
// Groups go from all-elements-present down to single elements, ending with "wrong or blank"
const SCHEMAS = {
  '1.a': [
    'liver_positive heart_negative',
    'liver_positive',
    'heart_negative',
    'wrong or blank'
  ],
  '1.b': [
    'value zero_x_interpretation',
    'value',
    'zero_x_interpretation',
    'wrong or blank'
  ],
  '1.d': [
    'percentage explained_variation dependent_variable',
    'percentage explained_variation',
    'percentage dependent_variable',
    'explained_variation dependent_variable',
    'percentage',
    'explained_variation',
    'dependent_variable',
    'wrong or blank'
  ],
  '1.e': [
    'value error_meaning units unit_attribution',
    'value error_meaning units',
    'value error_meaning unit_attribution',
    'value units unit_attribution',
    'error_meaning units unit_attribution',
    'value error_meaning',
    'value units',
    'value unit_attribution',
    'error_meaning units',
    'error_meaning unit_attribution',
    'units unit_attribution',
    'value',
    'error_meaning',
    'units',
    'unit_attribution',
    'wrong or blank'
  ],
  '1.f': [
    'means_property algebra answer',
    'means_property algebra',
    'means_property answer',
    'algebra answer',
    'means_property',
    'algebra',
    'answer',
    'wrong or blank'
  ],
  '2.a': [
    'joint conditional_error marginal_error',
    'joint conditional_error',
    'joint marginal_error',
    'conditional_error marginal_error',
    'joint',
    'conditional_error',
    'marginal_error',
    'wrong or blank'
  ],
  '2.c': [
    'conclusion product_rule definition',
    'conclusion product_rule',
    'conclusion definition',
    'product_rule definition',
    'conclusion',
    'product_rule',
    'definition',
    'wrong or blank'
  ],
  '2.d': [
    'marginal conditional_dist expectation_formula answer shown_work',
    'marginal conditional_dist expectation_formula answer',
    'marginal conditional_dist expectation_formula shown_work',
    'marginal conditional_dist answer shown_work',
    'marginal expectation_formula answer shown_work',
    'conditional_dist expectation_formula answer shown_work',
    'marginal conditional_dist expectation_formula',
    'marginal conditional_dist answer',
    'marginal conditional_dist shown_work',
    'marginal expectation_formula answer',
    'marginal expectation_formula shown_work',
    'marginal answer shown_work',
    'conditional_dist expectation_formula answer',
    'conditional_dist expectation_formula shown_work',
    'conditional_dist answer shown_work',
    'expectation_formula answer shown_work',
    'marginal conditional_dist',
    'marginal expectation_formula',
    'marginal answer',
    'marginal shown_work',
    'conditional_dist expectation_formula',
    'conditional_dist answer',
    'conditional_dist shown_work',
    'expectation_formula answer',
    'expectation_formula shown_work',
    'answer shown_work',
    'marginal',
    'conditional_dist',
    'expectation_formula',
    'answer',
    'shown_work',
    'wrong or blank'
  ],
  '2.e': [
    'LTE marginals substitution algebra answer',
    'LTE marginals substitution algebra',
    'LTE marginals substitution answer',
    'LTE marginals algebra answer',
    'LTE substitution algebra answer',
    'marginals substitution algebra answer',
    'LTE marginals substitution',
    'LTE marginals algebra',
    'LTE marginals answer',
    'LTE substitution algebra',
    'LTE substitution answer',
    'LTE algebra answer',
    'marginals substitution algebra',
    'marginals substitution answer',
    'marginals algebra answer',
    'substitution algebra answer',
    'LTE marginals',
    'LTE substitution',
    'LTE algebra',
    'LTE answer',
    'marginals substitution',
    'marginals algebra',
    'marginals answer',
    'substitution algebra',
    'substitution answer',
    'algebra answer',
    'LTE',
    'marginals',
    'substitution',
    'algebra',
    'answer',
    'wrong or blank'
  ],
  '3.a': [
    'variance_formula covariance answer',
    'variance_formula covariance',
    'variance_formula answer',
    'covariance answer',
    'variance_formula',
    'covariance',
    'answer',
    'wrong or blank'
  ],
  '3.b': [
    'linearity answer',
    'linearity',
    'answer',
    'wrong or blank'
  ],
  '3.c': [
    'covariance_expansion covariance answer',
    'covariance_expansion covariance',
    'covariance_expansion answer',
    'covariance answer',
    'covariance_expansion',
    'covariance',
    'answer',
    'wrong or blank'
  ]
};

// Titles to skip entirely (no schema defined, or already graded)
const SKIP_TITLES = new Set(['1.c', '1.g', '1.h', '1.i', '2.b']);

// Assignment IDs for each exam version
const ASSIGNMENT_IDS = {
  'VA': 8068292,
  'VB': 8068374,
  'VC': 8068382,
  'VD': 8068383
};

async function processAllExams() {
  const results = [];

  for (const [version, assignmentId] of Object.entries(ASSIGNMENT_IDS)) {
    console.log(`\n=== Processing ${version} (${assignmentId}) ===`);
    results.push(`\n=== ${version} (${assignmentId}) ===`);

    const questions = await getAssignmentQuestions(assignmentId);

    for (const q of questions) {
      const title = q.title;

      // Skip questions with no schema or already graded
      if (SKIP_TITLES.has(title)) {
        console.log(`  SKIP ${title}`);
        results.push(`  SKIP ${title}`);
        continue;
      }

      const targetGroups = SCHEMAS[title];
      if (!targetGroups) {
        console.log(`  SKIP ${title} (no schema)`);
        results.push(`  SKIP ${title} (no schema)`);
        continue;
      }

      console.log(`  Q${title} (id=${q.id}): ${targetGroups.length} groups`);
      results.push(`  Q${title} (id=${q.id}): ${targetGroups.length} groups`);

      // Step 1: Set grouping type to 'complex' (required before creating groups)
      const typeStatus = await setGroupingType(q.id);
      results.push(`    setType -> ${typeStatus}`);

      // Step 2: Get existing groups
      const existing = await getGroups(q.id);
      const existingTitleSet = new Set(existing.map(g => g.title));

      // Step 3: Delete any groups that don't belong (e.g. accidentally created ones)
      for (const eg of existing) {
        if (!targetGroups.includes(eg.title)) {
          const ds = await deleteGroupFn(q.id, eg.id);
          console.log(`    DEL "${eg.title || 'null'}" -> ${ds}`);
          results.push(`    DEL "${eg.title || 'null'}" -> ${ds}`);
        }
      }

      // Step 4: Create any missing groups
      for (const gt of targetGroups) {
        if (existingTitleSet.has(gt)) {
          results.push(`    EXISTS "${gt}"`);
          continue;
        }
        const cr = await createGroup(q.id, gt);
        console.log(`    CREATE "${gt}" -> ${cr.status}`);
        results.push(`    CREATE "${gt}" -> ${cr.status}`);
      }
    }
  }

  const summary = results.join('\n');
  const created = results.filter(l => l.includes('CREATE') && l.includes('-> 200')).length;
  const failed  = results.filter(l => l.match(/-> [45]\d\d/) && !l.includes('-> 200')).length;
  console.log(`\nBATCH COMPLETE: ${created} created, ${failed} failed`);
  return summary;
}

// Run it
processAllExams().then(r => {
  window._batchResults = r;
  console.log('BATCH COMPLETE. Full log saved to window._batchResults');
});
